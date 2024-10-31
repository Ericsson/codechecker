"""
super report hash

Revision ID: 1e3bd4b04bcd
Revises:     c3dad71f8e6b
Create Date: 2024-10-30 18:22:21.392600
"""

from logging import getLogger

from alembic import op
import sqlalchemy as sa



# Revision identifiers, used by Alembic.
revision = '1e3bd4b04bcd'
down_revision = 'c3dad71f8e6b'
branch_labels = None
depends_on = None


def upgrade():
    LOG = getLogger("migration/report")
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('reports', schema=None) as batch_op:
        # Add the new column
        batch_op.add_column(sa.Column('super_hash', sa.String(), nullable=False))
        # Create the index
        batch_op.create_index('ix_reports_super_hash', ['super_hash'], unique=False)
        # Create the unique constraint
        # batch_op.create_unique_constraint('uq_reports_super_hash', ['super_hash'])

    
    #op.add_column('reports', sa.Column('super_hash', sa.String(), nullable=False))
    #op.create_index(op.f('ix_reports_super_hash'), 'reports', ['super_hash'], unique=False)
    #op.create_constraint(op.f('uq_reports_super_hash'), 'reports', type_='unique')
    # ### end Alembic commands ###


def downgrade():
    LOG = getLogger("migration/report")
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_constraint(op.f('uq_reports_super_hash'), 'reports', type_='unique')
    op.drop_index(op.f('ix_reports_super_hash'), table_name='reports')
    op.drop_column('reports', 'super_hash')
    # ### end Alembic commands ###
