
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Map between database statuses and the corresponding messages.
"""


from codechecker_api_shared.ttypes import DBStatus

db_status_msg = {
    DBStatus.OK: "Database is up to date.",
    DBStatus.MISSING: "Database is missing.",
    DBStatus.FAILED_TO_CONNECT: "Connection failed to the database server.",
    DBStatus.SCHEMA_MISMATCH_OK:
        "Database schema mismatch! Possible to upgrade.",
    DBStatus.SCHEMA_MISMATCH_NO:
        "Database schema mismatch! NOT possible to upgrade.",
    DBStatus.SCHEMA_MISSING: "Database schema is missing.",
    DBStatus.SCHEMA_INIT_ERROR: "Schema initialization error.",
    DBStatus.SCHEMA_UPGRADE_FAILED: "Schema upgrade failed."
}
