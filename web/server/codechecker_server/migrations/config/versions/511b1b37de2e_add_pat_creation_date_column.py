"""
Add PAT creation date column

Revision ID: 511b1b37de2e
Revises:     5e1501dfd333
Create Date: 2026-07-20 15:35:59.392866
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = '511b1b37de2e'
down_revision = '5e1501dfd333'
branch_labels = None
depends_on = None


def upgrade():
    dialect = op.get_context().dialect.name

    op.add_column('personal_access_tokens',
                  sa.Column('creation_date', sa.DateTime(), nullable=True))

    # Due to a bug, previously the last_access column stored the
    # Personal Access Token's creation date.
    op.execute("UPDATE personal_access_tokens SET creation_date = last_access")

    # Finally, mark the column as NOT nullable.
    if dialect == 'sqlite':
        with op.batch_alter_table('personal_access_tokens') as batch_op:
            batch_op.alter_column('creation_date',
                                  existing_type=sa.DateTime(),
                                  nullable=False)
    else:
        op.alter_column('personal_access_tokens', 'creation_date',
                        existing_type=sa.DateTime(), nullable=False)


def downgrade():
    dialect = op.get_context().dialect.name

    if dialect == 'sqlite':
        with op.batch_alter_table('personal_access_tokens') as batch_op:
            batch_op.drop_column('creation_date')
    else:
        op.drop_column('personal_access_tokens', 'creation_date')
