# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from datetime import datetime
import sqlalchemy


__allowed_types = {
    "datetime": {
        "func": datetime.fromisoformat,
        "display": "date-time in ISO format",
        # TODO: SQLite has limited datetime support
        "db": sqlalchemy.types.String
    },
    "string": {
        "func": str,
        "display": "string",
        "db": sqlalchemy.types.String
    },
    "integer": {
        "func": int,
        "display": "integer",
        "db": sqlalchemy.types.Integer
    }
}


report_annotation_types = {
    "timestamp": __allowed_types["datetime"],
    "testcase": __allowed_types["string"],
    "chronological_order": __allowed_types["integer"]
}
