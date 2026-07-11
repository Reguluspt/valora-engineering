# ADR 0027: Workbench Session Cardinality and State Scope

## Status
Accepted

## Context
The workbench feature allows users to edit project assets in a session-scoped draft workspace. In order to guarantee strict tenant separation, database integrity, and prevent duplicate workspace states, we must formalize:
1. Session cardinality (how many active sessions a user can have per project).
2. The scope of actions and reads allowed on active versus inactive sessions.

## Decision
- **Session Cardinality**: A user is allowed to have at most **one** ACTIVE `WorkbenchSession` per project.
- **Session Creation**:
  - The first create request returns `HTTP 201 Created`.
  - Subsequent create requests while an active session exists returns `HTTP 200 OK` and resumes the existing session.
  - Concurrency safety: In concurrent request races, database constraints (`uq_active_session_per_user_project`) enforce this at the database level. Application logic catches unique constraint violations, rolls back to a savepoint, retrieves the active session, and returns it with `HTTP 200 OK`.
- **Audit Logging**:
  - Resumed sessions do not trigger a new session start audit event.
  - New session starts write both `workbench.session.started` and a `UserActionLog` entry atomically in the same transaction.
- **Session Scoping & Reading**:
  - All read and write actions on layout, grid view, selection, inline edits, checkpoints, undo/redo stacks, panel states, and notifications default to requiring an **ACTIVE** session.
  - If a session is closed/inactive, any read/write request returns a safe `HTTP 404 Not Found` (matching the response of nonexistent sessions or cross-tenant attempts).
  - The `/close` endpoint is the sole exception and can resolve an inactive session to perform an idempotent close.
- **Target Validation**: All selection target IDs must belong to the same project as the active session. If any target ID fails validation, the entire transaction is rolled back and no mutations are persisted.
- **Admin Override**: No admin override is permitted in S12-R-003. Only the session owner can interact with or read their session state.

## Migration Runbook Cleanup
If duplicate ACTIVE workbench sessions exist when running database migrations, the migration will halt to prevent data corruption.
To resolve this:

1. **Pre-requisite: Change Ticket Registration**
   - Ensure a change ticket (e.g. `CHG-S12-003`) is approved before executing any production updates.

2. **Step 1: Backup Database State**
   - Backup the `workbench_sessions` table before executing updates:
     ```sql
     CREATE TABLE backup_workbench_sessions_CHG_S12_003 AS SELECT * FROM workbench_sessions;
     ```

3. **Step 2: Identify Duplicates**
   - Run the validation query:
     ```sql
     SELECT user_id, project_id, COUNT(*) FROM workbench_sessions WHERE status = 'active' GROUP BY user_id, project_id HAVING COUNT(*) > 1;
     ```

4. **Step 3: Close Older Sessions (Keep Newest Active)**
   - Update status to 'closed' for older active sessions (the query partitions by user/project, orders by descending created date, and closes all but the newest active session):
     ```sql
     UPDATE workbench_sessions SET status = 'closed', updated_at = CURRENT_TIMESTAMP WHERE id IN (
         SELECT id FROM (
             SELECT id, ROW_NUMBER() OVER(PARTITION BY user_id, project_id ORDER BY created_at DESC) as rn
             FROM workbench_sessions WHERE status = 'active'
         ) t WHERE t.rn > 1
     );
     ```

5. **Step 4: Create Audit Record**
   - Record the clean up action in the audit log table as trace evidence:
     ```sql
     INSERT INTO audit_events (id, event_name, entity_type, entity_id, payload, created_at)
     SELECT gen_random_uuid(), 'workbench.session.cleanup', 'System', id, '{"reason": "migration_cardinality_enforcement", "previous_status": "active", "new_status": "closed"}'::jsonb, CURRENT_TIMESTAMP
     FROM backup_workbench_sessions_CHG_S12_003
     WHERE status = 'active' AND id NOT IN (
         SELECT id FROM (
             SELECT id, ROW_NUMBER() OVER(PARTITION BY user_id, project_id ORDER BY created_at DESC) as rn
             FROM backup_workbench_sessions_CHG_S12_003 WHERE status = 'active'
         ) t WHERE t.rn = 1
     );
     ```

6. **Step 5: Verify Checks**
   - Verify that no duplicates exist:
     ```sql
     SELECT COUNT(*) FROM workbench_sessions WHERE status = 'active' GROUP BY user_id, project_id HAVING COUNT(*) > 1;
     -- Expected result: 0 rows returned
     ```

7. **Step 6: Run Migrations**
   - Execute migrations: `alembic upgrade head`.
