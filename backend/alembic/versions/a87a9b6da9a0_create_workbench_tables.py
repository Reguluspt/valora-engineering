"""create_workbench_tables

Revision ID: a87a9b6da9a0
Revises: a87a9b6da99f
Create Date: 2026-07-08 25:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a87a9b6da9a0"
down_revision = "a87a9b6da99f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. workbench_sessions
    op.create_table(
        "workbench_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("current_selection", sa.JSON(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_workbench_sessions_user", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_workbench_sessions_project",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. workbench_layouts
    op.create_table(
        "workbench_layouts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("layout_name", sa.String(length=255), nullable=False),
        sa.Column("layout_payload", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_workbench_layouts_user", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. asset_grid_views
    op.create_table(
        "asset_grid_views",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("view_name", sa.String(length=255), nullable=False),
        sa.Column("columns", sa.JSON(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("sort", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_asset_grid_views_user", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="fk_asset_grid_views_project", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. workbench_selections
    op.create_table(
        "workbench_selections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("selected_target_type", sa.String(length=100), nullable=False),
        sa.Column("selected_target_ids", sa.JSON(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["workbench_sessions.id"],
            name="fk_workbench_selections_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. inline_edit_drafts
    op.create_table(
        "inline_edit_drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("field_key", sa.String(length=255), nullable=False),
        sa.Column("draft_value", sa.JSON(), nullable=False),
        sa.Column("base_value", sa.JSON(), nullable=True),
        sa.Column("base_row_version", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["workbench_sessions.id"],
            name="fk_inline_edit_drafts_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 6. autosave_checkpoints
    op.create_table(
        "autosave_checkpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("checkpoint_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["workbench_sessions.id"],
            name="fk_autosave_checkpoints_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 7. undo_redo_stack_entries
    op.create_table(
        "undo_redo_stack_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("field_key", sa.String(length=255), nullable=True),
        sa.Column("before_value", sa.JSON(), nullable=True),
        sa.Column("after_value", sa.JSON(), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("is_undone", sa.Boolean(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["workbench_sessions.id"],
            name="fk_undo_redo_entries_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 8. panel_states
    op.create_table(
        "panel_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("panel_type", sa.String(length=50), nullable=False),
        sa.Column("is_expanded", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["workbench_sessions.id"],
            name="fk_panel_states_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 9. review_queue_views
    op.create_table(
        "review_queue_views",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("filter_payload", sa.JSON(), nullable=False),
        sa.Column("sort_payload", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_review_queue_views_user", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 10. workbench_notifications
    op.create_table(
        "workbench_notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_workbench_notifications_user", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["workbench_sessions.id"],
            name="fk_workbench_notifications_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("workbench_notifications")
    op.drop_table("review_queue_views")
    op.drop_table("panel_states")
    op.drop_table("undo_redo_stack_entries")
    op.drop_table("autosave_checkpoints")
    op.drop_table("inline_edit_drafts")
    op.drop_table("workbench_selections")
    op.drop_table("asset_grid_views")
    op.drop_table("workbench_layouts")
    op.drop_table("workbench_sessions")
