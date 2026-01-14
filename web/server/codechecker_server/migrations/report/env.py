# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

from codechecker_server.database.run_db_model import Base
from codechecker_server.migrations.logging import set_logger_database_name

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Add model's MetaData object here for 'autogenerate' support.
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))

target_metadata = Base.metadata

schema = "report"

# Other values from the config, defined by the needs of env.py, can be
# acquired: my_important_option = config.get_main_option("my_important_option")


def run_migrations_online():
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    def migrate(connection):
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        set_logger_database_name(schema,
                                 config.attributes.get("database_name"))

        with context.begin_transaction():
            context.run_migrations()

    connection = config.attributes.get('connection', None)
    if connection:
        migrate(connection)
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix='sqlalchemy.',
            poolclass=pool.NullPool)

        with connectable.connect() as connection:
            migrate(connection)


if context.is_offline_mode():
    raise NotImplementedError(f"Offline '{schema}' migration is not possible!")
run_migrations_online()
