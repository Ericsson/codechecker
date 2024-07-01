# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Output to the user, formatting utilities."""
import sys

from emoji import emojize as emoji, replace_emoji
from termcolor import colored as coloured  # pylint: disable=unused-import

from .util import _Singleton


class Settings(_Singleton):
    """Package-level output settings."""

    def __init__(self):
        """Returns the instance that was loaded as a `_Singleton`."""
        if "_trace" not in self.__dict__:
            self._trace: bool = False

    @staticmethod
    def factory():
        """Initialises the `_Singleton`."""
        o = Settings()
        return o

    @staticmethod
    def trace() -> bool:
        return Settings.factory()._trace  # type: ignore

    @staticmethod
    def set_trace(v: bool):
        Settings.factory()._trace = v  # type: ignore


def _print(string: str, *args, **kwargs):
    """
    Wrapper over standard `print` which strips emojis if the output file is
    not a terminal.
    """
    try:
        isatty = kwargs["file"].isatty()
    except KeyError:
        isatty = sys.stdout.isatty() and sys.stderr.isatty()

    if not isatty:
        string = replace_emoji(string, '').strip()
    print(string, *args, **kwargs)


def log(fmt: str, *args, **kwargs):
    """Logging stub."""
    if "file" not in kwargs:
        kwargs["file"] = sys.stderr

    return _print(fmt % (args), **kwargs)


def _log_with_prefix(prefix: str, fmt: str, *args, **kwargs):
    """Logging stub."""
    fmt = f"{prefix}: {fmt}"
    return log(fmt, *args, **kwargs)


def error(fmt: str, *args, **kwargs):
    """Logging stub."""
    return _log_with_prefix(f"{emoji(':warning:  ')}ERROR",
                            fmt, *args, **kwargs)


def trace(fmt: str, *args, **kwargs):
    """Logging stub."""
    if Settings.trace():
        return _log_with_prefix(f'{emoji(":speech_balloon:  ")}TRACE',
                                fmt, *args, **kwargs)
    return None
