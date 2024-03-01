# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import logging
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

# This is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Add model's MetaData object here for 'autogenerate' support.
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from codechecker_server.database.run_db_model import Base

target_metadata = Base.metadata

# Other values from the config, defined by the needs of env.py, can be
# acquired: my_important_option = config.get_main_option("my_important_option")


class MigrationFormatter(logging.Formatter):
    """
    Truncates the filename to show only the revision that is being migrated
    in the log output.
    """
    def __init__(self):
        super().__init__(fmt="[%(levelname)s][%(asctime)s] "
                             "{migration/report} "
                             "[%(schemaVersion)s]:%(lineno)d "
                             "- %(message)s",
                         datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record):
        record.schemaVersion = record.filename[:record.filename.find("_")]
        return super().format(record)


def setup_logger():
    """
    Set up a logging system that should be used during schema migration.
    These outputs are not affected by the environment that executes a migration,
    e.g., by the running CodeChecker server!

    In migration scripts, use the built-in logging facilities instead of
    CodeChecker's wrapper, and ensure that the name of the logger created
    exactly matches "migration"!
    """
    sys_logger = logging.getLogger("system")
    codechecker_loglvl = sys_logger.getEffectiveLevel()
    if codechecker_loglvl >= logging.INFO:
        # This might be 30 (WARNING) if the migration is run outside of
        # CodeChecker's context, e.g., in a downgrade.
        codechecker_loglvl = logging.INFO

    # Use the default logging class that came with Python for the migration,
    # temporarily turning away from potentially existing global changes.
    existing_logger_cls = logging.getLoggerClass()
    logging.setLoggerClass(logging.Logger)
    logger = logging.getLogger("migration")
    logging.setLoggerClass(existing_logger_cls)

    if not logger.hasHandlers():
        fmt = MigrationFormatter()
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)
        handler.setLevel(codechecker_loglvl)
        handler.setStream(sys.stdout)

        logger.setLevel(codechecker_loglvl)
        logger.addHandler(handler)


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = config.attributes.get('connection', None)
    if connectable is None:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix='sqlalchemy.',
            poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

setup_logger()
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
