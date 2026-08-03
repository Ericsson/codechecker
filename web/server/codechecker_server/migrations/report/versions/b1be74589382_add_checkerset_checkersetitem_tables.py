"""
Add CheckerSet, CheckerSetItem tables

Revision ID: b1be74589382
Revises:     a7f3c8e21b90
Create Date: 2026-07-22 14:49:04.765801
"""

from logging import getLogger

from alembic import op
import sqlalchemy as sa
import json
from codechecker_server.database.run_db_model import CheckerSet


# Revision identifiers, used by Alembic.
revision = 'b1be74589382'
down_revision = 'a7f3c8e21b90'
branch_labels = None
depends_on = None


def upgrade():
    LOG = getLogger("migration/report")
    dialect = op.get_context().dialect.name
    conn = op.get_bind()

    op.create_table(
        'checker_set',
        sa.Column('id', sa.Integer(),
                  autoincrement=True, nullable=False),
        sa.Column('hash_digest', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_checker_set')),
        sa.UniqueConstraint('hash_digest',
                            name=op.f('uq_checker_set_hash_digest'))
    )
    op.create_table(
        'checker_set_items',
        sa.Column('checker_set_id', sa.Integer(),
                  nullable=False),
        sa.Column('checker_id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ['checker_id'], ['checkers.id'],
            name=op.f('fk_checker_set_items_checker_id_checkers'),
            ondelete='RESTRICT', initially='DEFERRED',
            deferrable=True),
        sa.ForeignKeyConstraint(
            ['checker_set_id'], ['checker_set.id'],
            name=op.f('fk_checker_set_items_checker_set_id_checker_set'),
            ondelete='CASCADE', initially='DEFERRED', deferrable=True),
        sa.PrimaryKeyConstraint('checker_set_id', 'checker_id',
                                name=op.f('pk_checker_set_items'))
    )
    op.add_column('analysis_info', sa.Column('checker_set_id',
                                             sa.Integer(), nullable=True))

    if dialect == "postgresql":
        op.create_foreign_key(op.f(
            'fk_analysis_info_checker_set_id_checker_set'),
            'analysis_info', 'checker_set', ['checker_set_id'],
            ['id'], ondelete='CASCADE', initially='DEFERRED', deferrable=True)
    elif dialect == "sqlite":
        # SQLite does not support adding foreign keys to an existing table,
        # so the analysis_info table is essentially dropped and recreated
        # again. For this, we need to disable the foreign key constraints.

        # op.execute("PRAGMA foreign_keys=OFF")
        # with op.batch_alter_table('analysis_info', schema=None) as batch_op:
        #     batch_op.create_foreign_key(
        #         batch_op.f('fk_analysis_info_checker_set_id_checker_set'),
        #         'checker_set',
        #         ['checker_set_id'], ['id'],
        #         ondelete='CASCADE', initially='DEFERRED', deferrable=True
        #     )

        # The operation above results in an error if executed
        # as part of a migration chain. Reason:
        # Foreign key constraints cannot be properly disabled
        # mid-transaction in case of SQLite.
        # See comment from other migration (c3dad71f8e6b):

        # It generally appears that the big issue here is the fact that
        # migration scripts execute as part of a TRANSACTION! As such,
        # the "PRAGMA foreign_keys=OFF" is useless. See the docs at
        #     http://sqlite.org/foreignkeys.html (quoted Jan 16, 2024)
        #
        # > It is not possible to enable or disable foreign key
        # > constraints in the middle of a multi-statement transaction
        # > (when SQLite is not in autocommit mode). Attempting to do
        # > so does not return an error; it simply has no effect.
        pass
    else:
        raise Exception(f"Dialect {dialect} is not supported!")

    LOG.info("Aggregating all checkers from table "
             f"analysis_info_checkers (dialect: {dialect}) ...")
    checker_sets = {}

    if dialect == "postgresql":
        # Note: For each CheckerSet, we want to generate a unique identifier,
        # to speed up report storage to the server.
        # CheckerSet.compute_hash() uses hashing algorithm SHA256
        # which is significantly slower than MD5.
        # Therefore, we use Postgresql's built-in md5 hash function to
        # calculate a hash that can be used to efficiently put checkers
        # into groups.
        query = \
            conn.execute(
                sa.text(
                    """SELECT analysis_info_id,
                       enabled_checkers,
                       disabled_checkers,
                       md5(enabled_checkers::text || '-'
                           || disabled_checkers::text) AS hash
                       FROM
                       (SELECT analysis_info_id,
                       array_agg(checker_id ORDER by checker_id)
                       FILTER (WHERE enabled) AS enabled_checkers,
                       array_agg(checker_id ORDER by checker_id)
                       FILTER (WHERE NOT enabled) AS disabled_checkers
                       FROM analysis_info_checkers
                       GROUP BY analysis_info_id)"""))
        for analysis_info_id, enabled_checkers, \
                disabled_checkers, md5sum in query:
            enabled_checkers = enabled_checkers or []
            disabled_checkers = disabled_checkers or []

            if md5sum not in checker_sets:
                checker_sets[md5sum] = {}
                checker_sets[md5sum]["hash_digest"] = \
                    CheckerSet.compute_hash(enabled_checkers,
                                            disabled_checkers)
                checker_sets[md5sum]["enabled_checkers"] = enabled_checkers
                checker_sets[md5sum]["disabled_checkers"] = disabled_checkers
                checker_sets[md5sum]["analysis_info_ids"] = [analysis_info_id]
            else:
                checker_sets[md5sum]["analysis_info_ids"]. \
                        append(analysis_info_id)
    elif dialect == "sqlite":
        # Note: SQLite does not support an md5 hash function,
        # therefore we need to compute the hash every time
        # in Python to determine the checker groups.
        #
        # Ordering in json_group_array is not needed in this case,
        # since no md5sum is computed.
        # Additionally, CheckerSet.compute_hash() always sorts checker
        # lists for hash generation.
        query = conn.execute(
                sa.text("""SELECT analysis_info_id,
                           json_group_array(checker_id)
                           FILTER (WHERE enabled) AS enabled_checkers,
                           json_group_array(checker_id)
                           FILTER (WHERE NOT enabled) AS disabled_checkers
                           FROM analysis_info_checkers
                           GROUP BY analysis_info_id"""))

        for analysis_info_id, enabled_checkers, disabled_checkers in query:
            enabled_checkers = json.loads(enabled_checkers) \
                if enabled_checkers != "[null]" else []
            disabled_checkers = json.loads(disabled_checkers) \
                if disabled_checkers != "[null]" else []
            hash_digest = CheckerSet.compute_hash(enabled_checkers,
                                                  disabled_checkers)

            if hash_digest not in checker_sets:
                checker_sets[hash_digest] = {}
                checker_sets[hash_digest]["hash_digest"] = \
                    hash_digest
                checker_sets[hash_digest]["enabled_checkers"] = \
                    enabled_checkers
                checker_sets[hash_digest]["disabled_checkers"] = \
                    disabled_checkers
                checker_sets[hash_digest]["analysis_info_ids"] = \
                    [analysis_info_id]
            else:
                checker_sets[hash_digest]["analysis_info_ids"]. \
                        append(analysis_info_id)
    else:
        raise Exception(f"Dialect {dialect} is not supported!")

    LOG.info("Inserting new CheckerSets to database ...")
    for v in checker_sets.values():
        conn.execute(
            sa.text("INSERT INTO checker_set (hash_digest) "
                    "VALUES (:hash_digest)"),
            {"hash_digest": v["hash_digest"]}
        )

        # Obtain CheckerSet ID
        select_q = conn.execute(
            sa.text("SELECT id from checker_set "
                    "WHERE hash_digest = :hash_digest"),
            {"hash_digest": v["hash_digest"]}
        ).fetchone()

        if not select_q:
            raise Exception("Failed to insert checker_set "
                            f"with hash_digest {v['hash_digest']}")

        # Bulk insert checkers
        if v["enabled_checkers"]:
            conn.execute(
                sa.text("INSERT INTO checker_set_items "
                        "(checker_set_id, checker_id, enabled) "
                        "VALUES (:checker_set_id, :checker_id, :enabled)"),
                [{"checker_set_id": select_q.id,
                  "checker_id": checker_id, "enabled": True}
                 for checker_id in v["enabled_checkers"]]
            )

        if v["disabled_checkers"]:
            conn.execute(
                sa.text("INSERT INTO checker_set_items "
                        "(checker_set_id, checker_id, enabled) "
                        "VALUES (:checker_set_id, :checker_id, :enabled)"),
                [{"checker_set_id": select_q.id,
                  "checker_id": checker_id, "enabled": False}
                 for checker_id in v["disabled_checkers"]]
            )

        # Update AnalysisInfo table checker_set_id column
        conn.execute(
            sa.text(
                "UPDATE analysis_info SET checker_set_id = :checker_set_id "
                "WHERE id IN :ids").bindparams(sa.bindparam(
                    "ids", expanding=True)),
            [{"checker_set_id": select_q.id, "ids": v["analysis_info_ids"]}]
        )

    LOG.info("Dropping table analysis_info_checkers ...")
    op.drop_table('analysis_info_checkers')
    # ### end Alembic commands ###


def downgrade():
    LOG = getLogger("migration/report")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
            op.f('fk_analysis_info_checker_set_id_checker_set'),
            'analysis_info', type_='foreignkey')
    op.drop_column('analysis_info', 'checker_set_id')
    op.create_table(
        'analysis_info_checkers',
        sa.Column('analysis_info_id', sa.INTEGER(), autoincrement=False,
                  nullable=False),
        sa.Column('checker_id', sa.INTEGER(), autoincrement=False,
                  nullable=False),
        sa.Column('enabled', sa.BOOLEAN(), autoincrement=False,
                  nullable=True),
        sa.ForeignKeyConstraint(
            ['analysis_info_id'], ['analysis_info.id'],
            name=op.f(
                'fk_analysis_info_checkers_analysis_info_id_analysis_info'),
            ondelete='CASCADE', initially='DEFERRED', deferrable=True),
        sa.ForeignKeyConstraint(
            ['checker_id'], ['checkers.id'],
            name=op.f(
                'fk_analysis_info_checkers_checker_id_checkers'),
            ondelete='RESTRICT', initially='DEFERRED', deferrable=True),
        sa.PrimaryKeyConstraint('analysis_info_id', 'checker_id',
                                name=op.f('pk_analysis_info_checkers'))
    )
    op.drop_table('checker_set_items')
    op.drop_table('checker_set')
    # ### end Alembic commands ###
