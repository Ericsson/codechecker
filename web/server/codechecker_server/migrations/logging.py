# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import logging
import sys


class MigrationFormatter(logging.Formatter):
    """
    Truncates the filename to show only the revision that is being migrated
    in the log output.
    """
    def __init__(self, schema: str):
        super().__init__(fmt="[%(levelname)s][%(asctime)s] "
                             "{migration/%(schema)s} "
                             "[%(schemaVersion)s]:%(lineno)d "
                             "- %(message)s",
                         datefmt="%Y-%m-%d %H:%M:%S")
        self.schema = schema

    def format(self, record):
        record.schema = self.schema
        record.schemaVersion = record.filename[:record.filename.find("_")]
        return super().format(record)


def setup_logger(schema: str):
    """
    Set up a logging system that should be used during schema migration.
    These outputs are not affected by the environment that executes a
    migration, e.g., by the running CodeChecker server!

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
