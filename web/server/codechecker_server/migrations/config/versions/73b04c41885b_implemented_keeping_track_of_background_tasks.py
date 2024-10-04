"""
Implemented keeping track of background tasks through corresponding records
in the server-wide configuration database.

Revision ID: 73b04c41885b
Revises:     00099e8bc212
Create Date: 2023-09-21 14:24:27.395597
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = '73b04c41885b'
down_revision = '00099e8bc212'
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
