"""Grant existing Workbench open permission under accepted A5R D1.

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, None] = "a4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PERMISSION = "workbench:open"
_TARGET_ROLES = ("owner", "appraiser")
_GRANT_EVENT = "G2A5R2StandardOperatorWorkbenchOpenGrantAdded"
_ROLES = sa.table(
    "roles",
    sa.column("id", sa.Uuid()),
    sa.column("code", sa.String(64)),
    sa.column("permissions", sa.JSON()),
)
_AUDIT = sa.table(
    "audit_events",
    sa.column("id", sa.Uuid()),
    sa.column("event_name", sa.String(128)),
    sa.column("entity_type", sa.String(128)),
    sa.column("entity_id", sa.Uuid()),
    sa.column("command_name", sa.String(128)),
    sa.column("payload", sa.JSON()),
    sa.column("created_at", sa.DateTime(timezone=True)),
)


def _update_grants(*, add: bool) -> None:
    connection = op.get_bind()
    # One timestamp binds the atomic upgrade pair; older cycles cannot fill a missing latest audit.
    grant_at = connection.execute(
        sa.select(sa.func.now()) if add else
        sa.select(sa.func.max(_AUDIT.c.created_at)).where(_AUDIT.c.event_name == _GRANT_EVENT)
    ).scalar_one()
    for code in _TARGET_ROLES:
        role = connection.execute(
            sa.select(_ROLES.c.id, _ROLES.c.permissions)
            .where(_ROLES.c.code == code)
            .with_for_update()
        ).one_or_none()
        if role is None:
            raise ValueError(f"Missing standard role {code}")
        role_id, current = role
        if (
            not isinstance(current, list)
            or not all(isinstance(item, str) for item in current)
            or len(current) != len(set(current))
        ):
            raise ValueError(f"Invalid permissions for standard role {code}")

        if add:
            changed = [_PERMISSION] if _PERMISSION not in current else []
            updated = current + changed
        else:
            # Check bindings after selecting the latest pair, so malformed records cannot be skipped.
            records = connection.execute(
                sa.select(_AUDIT.c.entity_type, _AUDIT.c.command_name, _AUDIT.c.payload)
                .where(
                    _AUDIT.c.event_name == _GRANT_EVENT,
                    _AUDIT.c.entity_id == role_id,
                    _AUDIT.c.created_at == grant_at,
                )
                .limit(2)
            ).all()
            record = records[0].payload if records else None
            if (
                not isinstance(record, dict)
                or len(records) != 1
                or records[0].entity_type != "Role"
                or records[0].command_name != revision
                or record.get("role_code") != code
                or record.get("added_permissions") not in ([], [_PERMISSION])
                or _PERMISSION not in current
            ):
                raise ValueError(f"Invalid A5R2 grant provenance for standard role {code}")
            changed = record["added_permissions"]
            updated = [permission for permission in current if permission not in changed]

        if updated != current:
            connection.execute(
                sa.update(_ROLES).where(_ROLES.c.id == role_id).values(permissions=updated)
            )
        if add:
            connection.execute(sa.insert(_AUDIT).values(
                id=uuid.uuid4(), event_name=_GRANT_EVENT, entity_type="Role",
                entity_id=role_id, command_name=revision,
                payload={"role_code": code, "added_permissions": changed},
                created_at=grant_at,
            ))


def upgrade() -> None:
    _update_grants(add=True)


def downgrade() -> None:
    _update_grants(add=False)
