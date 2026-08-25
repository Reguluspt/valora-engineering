"""S14-PR-003 create asset identity decisions and learning feedback events

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-08-25 22:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd6e7f8a9b0c1'
down_revision: Union[str, None] = 'c5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'asset_identity_decisions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=True),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('raw_observation_id', sa.Uuid(), nullable=False),
        sa.Column('decision_type', sa.String(length=50), nullable=False),  # accepted, corrected, rejected, deferred
        sa.Column('chosen_canonical_asset_id', sa.Uuid(), nullable=True),
        sa.Column('chosen_asset_variant_id', sa.Uuid(), nullable=True),
        sa.Column('chosen_alias_id', sa.Uuid(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('actor_user_id', sa.Uuid(), nullable=False),
        sa.Column('command_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['raw_observation_id'], ['raw_asset_observations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'command_id', name='uq_asset_identity_decision_command')
    )
    op.create_index('idx_identity_dec_org', 'asset_identity_decisions', ['organization_id'])
    op.create_index('idx_identity_dec_obs', 'asset_identity_decisions', ['raw_observation_id'])
    op.create_index('idx_identity_dec_project', 'asset_identity_decisions', ['project_id'])

    op.create_table(
        'learning_feedback_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=True),
        sa.Column('source_decision_id', sa.Uuid(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),  # positive_match, negative_match
        sa.Column('raw_wording', sa.Text(), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),  # CanonicalAsset, AssetVariant, ContextualAlias
        sa.Column('target_id', sa.Uuid(), nullable=False),
        sa.Column('feedback_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['source_decision_id'], ['asset_identity_decisions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_feedback_org', 'learning_feedback_events', ['organization_id'])
    op.create_index('idx_feedback_decision', 'learning_feedback_events', ['source_decision_id'])


def downgrade() -> None:
    op.drop_table('learning_feedback_events')
    op.drop_table('asset_identity_decisions')
