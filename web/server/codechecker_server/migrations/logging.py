# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import logging
import sys
from typing import Optional, cast


class MigrationFormatter(logging.Formatter):
    """
    Truncates the filename to show only the revision that is being migrated
    in the log output.
    """
    def __init__(self, schema: str):
        super().__init__(fmt="[%(levelname)s][%(asctime)s] "
                             "{migration/%(schema)s} "
                             "[%(database)s] "
                             "- %(revision)s:%(lineno)d "
                             "- %(message)s",
                         datefmt="%Y-%m-%d %H:%M:%S")
        self.schema = schema
        self._database: Optional[str] = None

    @property
    def database(self):
        return self._database or "<UNKNOWN!>"

    @database.setter
    def database(self, db_name: str):
        self._database = db_name

    def format(self, record):
        record.database = self.database
        record.schema = self.schema
        record.revision = record.filename[:record.filename.find("_")]
        return super().format(record)


def setup_logger(schema: str):
    """
    Set up a logging system that should be used during schema migration.
    These outputs are not affected by the environment that executes a
    migration, e.g., by the running CodeChecker server!

    In migration scripts, use the built-in logging facilities instead of
    CodeChecker's wrapper, and ensure that the name of the logger created
    exactly matches ``migration/<some schema>``!
    """
    sys_logger = logging.getLogger("system")
    codechecker_loglvl = sys_logger.getEffectiveLevel()
    # This might be 30 (WARNING) if the migration is run outside of
    # CodeChecker's context, e.g., in a downgrade.
    codechecker_loglvl = min(codechecker_loglvl, logging.INFO)

    # Use the default logging class that came with Python for the migration,
    # temporarily turning away from potentially existing global changes.
    existing_logger_cls = logging.getLoggerClass()
    logging.setLoggerClass(logging.Logger)
    logger = logging.getLogger(f"migration/{schema}")
    logging.setLoggerClass(existing_logger_cls)

    if not logger.hasHandlers():
        fmt = MigrationFormatter(schema)
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)
        handler.setLevel(codechecker_loglvl)
        handler.setStream(sys.stdout)

        logger.setLevel(codechecker_loglvl)
        logger.addHandler(handler)
    else:
        handler = logger.handlers[0]
        fmt = handler.formatter

    return logger, handler, cast(MigrationFormatter, fmt)


def set_logger_database_name(schema: str, database: str):
    """
    Sets the logger's output for the current migration ``schema`` to indicate
    that the actions are performed on ``database``.
    """
    _, _, fmt = setup_logger(schema)
    fmt.database = database
