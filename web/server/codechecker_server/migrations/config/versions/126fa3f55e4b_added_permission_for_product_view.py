"""Added permission for Product View

Revision ID: 7ceea9232211
Revises: 302693c76eb8
Create Date: 2021-05-25 09:43:15.402946

"""

# revision identifiers, used by Alembic.
revision = '7ceea9232211'
down_revision = '302693c76eb8'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


table_name = 'permissions_product'
column_name = 'permission'
type_name = 'product_perms'
tmp_type_name = f"tmp_{type_name}"

old_options = ('PRODUCT_ADMIN', 'PRODUCT_STORE', 'PRODUCT_ACCESS')
new_options = old_options + ('PRODUCT_VIEW', )

new_type = sa.Enum(*new_options, name=type_name)
old_type = sa.Enum(*old_options, name=type_name)


def upgrade():
    ctx = op.get_context()
    dialect = ctx.dialect.name

    if dialect == 'postgresql':
        # Rename the enum type what we want to change.
        op.execute(f"ALTER TYPE {type_name} RENAME TO {tmp_type_name}")

        # Create the new enum.
        new_type.create(op.get_bind())

        # # Alter detection status column.
        op.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} "
                   f"TYPE {type_name} USING {column_name}::text::{type_name}")

        # Drop the old enum.
        op.execute(f"DROP TYPE {tmp_type_name}")
    elif dialect == 'sqlite':
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                column_name, existing_type=old_type, type_=new_type)


def downgrade():
    ctx = op.get_context()
    dialect = ctx.dialect.name

    if dialect == 'postgresql':
        # Rename the enum type what we want to change.
        op.execute(f"ALTER TYPE {type_name} RENAME TO {tmp_type_name}")

        # Create the new enum.
        old_type.create(op.get_bind())

        # Alter detection status column.
        op.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} "
                   f"TYPE {type_name} USING {column_name}::text::{type_name}")

        # Drop the old enum.
        op.execute(f"DROP TYPE {tmp_type_name}")
    elif dialect == 'sqlite':
        with op.batch_alter_table('table_name') as batch_op:
            batch_op.alter_column(
                column_name, existing_type=new_type, type_=old_type)
