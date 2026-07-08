"""create_workflow_tables

Revision ID: a87a9b6da99f
Revises: a87a9b6da99e
Create Date: 2026-07-08 24:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a87a9b6da99f'
down_revision = 'a87a9b6da99e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. workflow_definitions
    op.create_table(
        'workflow_definitions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # 2. workflow_instances
    op.create_table(
        'workflow_instances',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('workflow_definition_id', sa.UUID(), nullable=False),
        sa.Column('target_type', sa.String(length=100), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('current_state', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['workflow_definition_id'], ['workflow_definitions.id'], name='fk_workflow_instances_def', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. workflow_transitions
    op.create_table(
        'workflow_transitions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workflow_definition_id', sa.UUID(), nullable=False),
        sa.Column('from_state', sa.String(length=100), nullable=False),
        sa.Column('to_state', sa.String(length=100), nullable=False),
        sa.Column('command_name', sa.String(length=100), nullable=False),
        sa.Column('required_permission', sa.String(length=100), nullable=True),
        sa.Column('guard_expression', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['workflow_definition_id'], ['workflow_definitions.id'], name='fk_workflow_transitions_def', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. workflow_tasks
    op.create_table(
        'workflow_tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('workflow_instance_id', sa.UUID(), nullable=False),
        sa.Column('task_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=False),
        sa.Column('assigned_to', sa.UUID(), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workflow_instance_id'], ['workflow_instances.id'], name='fk_workflow_tasks_instance', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], name='fk_workflow_tasks_assignee', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. review_decisions
    op.create_table(
        'review_decisions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('target_type', sa.String(length=100), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('decided_by', sa.UUID(), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('evidence_ids', sa.JSON(), nullable=True),
        sa.Column('previous_state', sa.String(length=100), nullable=True),
        sa.Column('new_state', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['decided_by'], ['users.id'], name='fk_review_decisions_decider', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. approval_gates
    op.create_table(
        'approval_gates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('gate_code', sa.String(length=64), nullable=False),
        sa.Column('target_type', sa.String(length=100), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('gate_status', sa.String(length=50), nullable=False),
        sa.Column('blocking_issue_count', sa.Integer(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 7. validation_rules
    op.create_table(
        'validation_rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rule_code', sa.String(length=64), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_blocking', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_code')
    )

    # 8. validation_issues
    op.create_table(
        'validation_issues',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('validation_rule_id', sa.UUID(), nullable=False),
        sa.Column('target_type', sa.String(length=100), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('issue_message', sa.Text(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('resolved_by', sa.UUID(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['validation_rule_id'], ['validation_rules.id'], name='fk_validation_issues_rule', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], name='fk_validation_issues_resolver', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # 9. user_action_logs
    op.create_table(
        'user_action_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('target_type', sa.String(length=100), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('action_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_action_logs_user', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('user_action_logs')
    op.drop_table('validation_issues')
    op.drop_table('validation_rules')
    op.drop_table('approval_gates')
    op.drop_table('review_decisions')
    op.drop_table('workflow_tasks')
    op.drop_table('workflow_transitions')
    op.drop_table('workflow_instances')
    op.drop_table('workflow_definitions')
