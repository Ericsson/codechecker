"""Disable review status change

Revision ID: 3335ff7593cc
Revises: 4964142b58d2
Create Date: 2018-11-29 14:16:58.170551

"""

# revision identifiers, used by Alembic.
revision = '3335ff7593cc'
down_revision = '4964142b58d2'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ctx = op.get_context()
    dialect = ctx.dialect.name

    new_col = sa.Column('is_review_status_change_disabled',
                        sa.Boolean(),
                        server_default=sa.sql.false())

    # To eliminate 'Skipping unsupported ALTER for creation of implicit
    # constraint' warning we use batch operation to create the new column in
    # case of SQLite.
    if dialect == 'sqlite':
        with op.batch_alter_table('products') as batch_op:
            batch_op.add_column(new_col)
    else:
        op.add_column('products', new_col)


def downgrade():
    op.drop_column('products', 'is_review_status_change_disabled')
