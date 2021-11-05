"""Global permission to get access controls

Revision ID: 7829789fc19c
Revises: cf025b6d7998
Create Date: 2021-10-28 11:29:08.775219

"""

# revision identifiers, used by Alembic.
revision = '7829789fc19c'
down_revision = 'cf025b6d7998'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


table_name = 'permissions_system'
column_name = 'permission'
type_name = 'sys_perms'
tmp_type_name = f"tmp_{type_name}"

old_options = ('SUPERUSER', )
new_options = old_options + ('PERMISSION_VIEW', )

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
