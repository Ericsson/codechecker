# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import base64


def to_b64(string):
    """ encode a string to a base64 encoded string """
    return base64.b64encode(string.encode("utf-8")).decode(
        "utf-8", errors="ignore"
    )


def from_b64(string_b64):
    """ decode a b46 encoded string to a string """
    return base64.b64decode(string_b64.encode("utf-8")).decode(
        "utf-8", errors="ignore"
    )
