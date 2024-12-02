# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Tool-level output settings."""
from ..util import _Singleton


class Settings(_Singleton):
    """Tool-level output settings."""

    def __init__(self):
        """Returns the instance that was loaded as a `_Singleton`."""
        if "_report_ok" not in self.__dict__:
            self._report_ok: bool = False

    @staticmethod
    def factory():
        """Initialises the `_Singleton`."""
        o = Settings()
        return o

    @staticmethod
    def report_ok() -> bool:
        return Settings.factory()._report_ok  # type: ignore

    @staticmethod
    def set_report_ok(v: bool):
        Settings.factory()._report_ok = v  # type: ignore
