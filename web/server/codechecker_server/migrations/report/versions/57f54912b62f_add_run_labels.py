"""
add run labels

Revision ID: 57f54912b62f
Revises:     feb5f01b5b52
Create Date: 2026-10-06 08:56:56.071397
"""

from logging import getLogger

from alembic import op
import sqlalchemy as sa



# Revision identifiers, used by Alembic.
revision = '57f54912b62f'
down_revision = 'feb5f01b5b52'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'run_labels',
        sa.Column(
            'id',
            sa.BigInteger().with_variant(sa.Integer, "sqlite"),
            autoincrement=True,
            nullable=False
        ),
        sa.Column('label_name', sa.String, nullable=False),
        sa.Column('description', sa.String, nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_run_labels'),
    )

    op.create_table(
        'run_to_run_labels',
        sa.Column(
            'run_id',
            sa.BigInteger().with_variant(sa.Integer, "sqlite"),
            nullable=False
        ),
        sa.Column(
            'run_label_id',
            sa.BigInteger().with_variant(sa.Integer, "sqlite"),
            nullable=False
        ),
        sa.ForeignKeyConstraint(
            ['run_id'],
            ['runs.id'],
            name='fk_run_to_run_labels_run_id_runs',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['run_label_id'],
            ['run_labels.id'],
            name='fk_run_to_run_labels_run_label_id_run_labels',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint(
            'run_id',
            'run_label_id',
            name='pk_run_to_run_labels'
        )
    )

    op.create_index(
        'ix_run_to_run_labels_run_label_id',
        'run_to_run_labels',
        ['run_label_id'],
        unique=False
    )


def downgrade():
    op.drop_index(
        'ix_run_to_run_labels_run_label_id',
        table_name='run_to_run_labels'
    )
    op.drop_table('run_to_run_labels')
    op.drop_table('run_labels')
