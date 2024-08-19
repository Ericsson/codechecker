"""
Implemented keeping track of background tasks through corresponding records
in the server-wide configuration database.

Revision ID: 5e1501dfd333
Revises:     7ed50f8b3fb8
Create Date: 2025-06-13 14:05:15.517337
"""

from logging import getLogger

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = '5e1501dfd333'
down_revision = '7ed50f8b3fb8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "background_tasks",
        sa.Column("machine_id", sa.String(), nullable=True),
        sa.Column("token", sa.CHAR(length=64), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("status", sa.Enum("allocated",
                                    "enqueued",
                                    "running",
                                    "completed",
                                    "failed",
                                    "cancelled",
                                    "dropped",
                                    name="background_task_statuses"),
                  nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("enqueued_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("consumed", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column("cancel_flag", sa.Boolean(), nullable=False,
                  server_default=sa.false()),

        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name=op.f("fk_background_tasks_product_id_products"),
            deferrable=False,
            ondelete="CASCADE",
            initially="IMMEDIATE"),
        sa.PrimaryKeyConstraint("token", name=op.f("pk_background_tasks"))
    )
    op.create_index(op.f("ix_background_tasks_kind"), "background_tasks",
                    ["kind"], unique=False)
    op.create_index(op.f("ix_background_tasks_machine_id"), "background_tasks",
                    ["machine_id"], unique=False)
    op.create_index(op.f("ix_background_tasks_product_id"), "background_tasks",
                    ["product_id"], unique=False)
    op.create_index(op.f("ix_background_tasks_status"), "background_tasks",
                    ["status"], unique=False)


def downgrade():
    ctx = op.get_context()
    dialect = ctx.dialect.name

    op.drop_index(op.f("ix_background_tasks_status"), "background_tasks")
    op.drop_index(op.f("ix_background_tasks_product_id"), "background_tasks")
    op.drop_index(op.f("ix_background_tasks_machine_id"), "background_tasks")
    op.drop_index(op.f("ix_background_tasks_kind"), "background_tasks")

    op.drop_table("action_history")

    if dialect == "postgresql":
        op.execute("DROP TYPE background_task_statuses;")
