# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Generic test decorators.
"""

from functools import wraps


def makeSkipUnlessAttributeFound(attribute, message):
    def decorator(original):
        @wraps(original)
        def wrapper(self, *args, **kwargs):
            if not getattr(self, attribute):
                self.skipTest(message)
            else:
                original(self, *args, **kwargs)
        return wrapper
    return decorator
