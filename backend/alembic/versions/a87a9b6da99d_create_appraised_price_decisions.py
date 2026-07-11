"""create_appraised_price_decisions

Revision ID: a87a9b6da99d
Revises: a87a9b6da99c
Create Date: 2026-07-07 24:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a87a9b6da99d'
down_revision = 'a87a9b6da99c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create appraised_price_decisions
    op.create_table(
        'appraised_price_decisions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('canonical_asset_id', sa.UUID(), nullable=True),
        sa.Column('asset_variant_id', sa.UUID(), nullable=True),
        sa.Column('quote_batch_id', sa.UUID(), nullable=True),
        sa.Column('final_unit_price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['canonical_asset_id'], ['canonical_assets.id'], name='fk_appraised_price_canonical', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['asset_variant_id'], ['asset_variants.id'], name='fk_appraised_price_variant', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['quote_batch_id'], ['quote_batches.id'], name='fk_appraised_price_quote_batch', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_appraised_price_creator', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], name='fk_appraised_price_approver', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('appraised_price_decisions')
