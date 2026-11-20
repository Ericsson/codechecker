"""
Added permission for PRODUCT_CACHE

Revision ID: a7c3e1f2b9d4
Revises:     635389f535cd
Create Date: 2026-11-13 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = 'a7c3e1f2b9d4'
down_revision = '635389f535cd'
branch_labels = None
depends_on = None

table_name = 'permissions_product'
column_name = 'permission'
type_name = 'product_perms'
tmp_type_name = f"tmp_{type_name}"

old_options = ('PRODUCT_ADMIN', 'PRODUCT_STORE', 'PRODUCT_ACCESS',
               'PRODUCT_VIEW')
new_options = old_options + ('PRODUCT_CACHE', )

new_type = sa.Enum(*new_options, name=type_name)
old_type = sa.Enum(*old_options, name=type_name)


def _change_type(from_type, to_type):
    ctx = op.get_context()
    dialect = ctx.dialect.name

    if dialect == 'postgresql':
        # Rename the enum type what we want to change.
        op.execute(sa.text(
            f"ALTER TYPE {type_name} RENAME TO {tmp_type_name}"))

        # Create the new enum.
        to_type.create(op.get_bind())

        # Alter the permission column.
        op.execute(sa.text(
            f"ALTER TABLE {table_name} ALTER COLUMN {column_name} "
            f"TYPE {type_name} USING {column_name}::text::{type_name}"))

        # Drop the old enum.
        op.execute(sa.text(f"DROP TYPE {tmp_type_name}"))
    elif dialect == 'sqlite':
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                column_name, existing_type=from_type, type_=to_type)


def upgrade():
    _change_type(old_type, new_type)


def downgrade():
    # Permission records of the removed value cannot be represented by the
    # old enum type.
    op.execute(sa.text(
        f"DELETE FROM {table_name} WHERE {column_name} = 'PRODUCT_CACHE'"))
    _change_type(new_type, old_type)
