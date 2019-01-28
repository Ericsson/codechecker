"""Off and unavailable detection statuses

Revision ID: 3e91d0612422
Revises: 40112fd406e3
Create Date: 2018-12-19 11:16:57.107510

"""

# revision identifiers, used by Alembic.
revision = '3e91d0612422'
down_revision = '40112fd406e3'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

table_name = 'reports'
name = 'detection_status'
tmp_name = 'tmp_' + name

old_options = ('new', 'unresolved', 'resolved', 'reopened')
new_options = old_options + ('off', 'unavailable', )

new_type = sa.Enum(*new_options, name=name)
old_type = sa.Enum(*old_options, name=name)


def upgrade():
    ctx = op.get_context()
    dialect = ctx.dialect.name

    if dialect == 'postgresql':
        # Rename the enum type what we want to change.
        op.execute('ALTER TYPE ' + name + ' RENAME TO ' + tmp_name)

        # Create the new enum.
        new_type.create(op.get_bind())

        # Alter detection status column.
        op.execute('ALTER TABLE ' + table_name + ' ALTER COLUMN ' + name +
                   ' TYPE ' + name + ' USING ' + name + '::text::' + name)

        # Drop the old enum.
        op.execute('DROP TYPE ' + tmp_name)
    elif dialect == 'sqlite':
        op.execute('PRAGMA foreign_keys=off')
        with op.batch_alter_table('reports') as batch_op:
            batch_op.alter_column(name, existing_type=old_type, type_=new_type)
        op.execute('PRAGMA foreign_keys=on')


def downgrade():
    ctx = op.get_context()
    dialect = ctx.dialect.name

    if dialect == 'postgresql':
        # Rename the enum type what we want to change.
        op.execute('ALTER TYPE ' + name + ' RENAME TO ' + tmp_name)

        # Create the new enum.
        old_type.create(op.get_bind())

        # Alter detection status column.
        op.execute('ALTER TABLE ' + table_name + ' ALTER COLUMN ' + name +
                   ' TYPE ' + name + ' USING ' + name + '::text::' + name)

        # Drop the old enum.
        op.execute('DROP TYPE ' + tmp_name)
    elif dialect == 'sqlite':
        op.execute('PRAGMA foreign_keys=off')
        with op.batch_alter_table('reports') as batch_op:
            batch_op.alter_column(name, existing_type=new_type, type_=old_type)
        op.execute('PRAGMA foreign_keys=on')
