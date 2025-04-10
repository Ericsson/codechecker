# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Argument parsing related helper classes and functions."""


import argparse
import collections
import os
import re


AnalyzerConfig = collections.namedtuple(
    'AnalyzerConfig', ["analyzer", "option", "value"])
CheckerConfig = collections.namedtuple(
    "CheckerConfig", ["analyzer", "checker", "option", "value"])
AnalyzerBinary = collections.namedtuple(
    "AnalyzerBinary", ["analyzer", "path"])


class OrderedCheckersAction(argparse.Action):
    """
    Action to store enabled and disabled checkers
    and keep ordering from command line.

    Create separate lists based on the checker names for
    each analyzer.
    """

    # Users can supply invocation to 'codechecker-analyze' as follows:
    # -e core -d core.uninitialized -e core.uninitialized.Assign
    # We must support having multiple '-e' and '-d' options and the order
    # specified must be kept when the list of checkers are assembled for Clang.

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, value, option_string=None):

        if 'ordered_checkers' not in namespace:
            namespace.ordered_checkers = []
        ordered_checkers = namespace.ordered_checkers
        # Map each checker to whether its enabled or not.
        ordered_checkers.append((value, self.dest == 'enable'))

        namespace.ordered_checkers = ordered_checkers


class OrderedConfigAction(argparse.Action):
    """
    Action to store --analyzer-config and --checker-config values. These may
    come from many sources, including the CLI, the CodeChecker config file,
    the saargs file and the tidyargs file, or some other places.
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs != '*':
            raise ValueError("nargs must be '*' for backward compatibility "
                             "reasons!")
        super().__init__(option_strings, dest, nargs, **kwargs)

    def __call__(self, parser, namespace, value, option_string=None):

        assert isinstance(value, list), \
               f"--analyzer-config or --checker-config value ({value}) is " \
               "not a list, but should be if nargs is not None!"

        # When the default value is empty list, it's passed by reference and
        # that default object will be used for further computations.
        # For example: CodeChecker analyze --analyzer-config blabla --help
        # This command above presents wrongly [blabla] as default value for
        # --analyzer-config, because the code below inserts this value to the
        # default empty list even if --help is printed.
        # For this list we change falsey default values to another empty list
        # object.
        if not hasattr(namespace, self.dest) or \
                not getattr(namespace, self.dest):
            setattr(namespace, self.dest, [])

        dest = getattr(namespace, self.dest)

        for flag in value:
            if flag in dest:
                dest.remove(flag)
            dest.append(flag)


def existing_abspath(path: str) -> str:
    """
    This function can be used at "type" argument of argparse.add_argument()
    function. It returns the absolute path of the given path if exists
    otherwise raises an argparse.ArgumentTypeError which constitutes in a
    graceful error message automatically by argparse module.
    """
    path = os.path.abspath(path)

    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"File doesn't exist: {path}")

    return path


def analyzer_config(arg: str) -> AnalyzerConfig:
    """
    This function can be used at "type" argument of argparse.add_argument().
    It checks the format of --analyzer-config flag:
    <analyzer>:<option>=<value>
    These three things return as a tuple.
    """
    m = re.match(r"(?P<analyzer>.+):(?P<option>.+)=(?P<value>.+)", arg)

    if not m:
        raise argparse.ArgumentTypeError(
            f"Analyzer option in wrong format: {arg}, should be "
            "<analyzer>:<option>=<value>")

    return AnalyzerConfig(
        m.group("analyzer"), m.group("option"), m.group("value"))


def checker_config(arg: str) -> CheckerConfig:
    """
    This function can be used at "type" argument of argparse.add_argument().
    It checks the format of --checker-config flag:
    <analyzer>:<checker>:<option>=<value>
    These four things return as a tuple.
    """
    m = re.match(
        r"(?P<analyzer>.+):(?P<checker>.+):(?P<option>.+)=(?P<value>.+)", arg)

    if not m:
        raise argparse.ArgumentTypeError(
            f"Checker option in wrong format: {arg}, should be "
            "<analyzer>:<checker>:<option>=<value>")

    return CheckerConfig(
        m.group("analyzer"), m.group("checker"),
        m.group("option"), m.group("value"))


def analyzer_binary(arg: str) -> AnalyzerBinary:
    """
    This function can be used at "type" argument of argparse.add_argument().
    It checks the format of --analyzer_binary flag: <analyzer>:<path>
    """
    m = re.match(r"(?P<analyzer>.+):(?P<path>.+)", arg)

    if not m:
        raise argparse.ArgumentTypeError(
            f"Analyzer binary in wrong format: {arg}, should be "
            "<analyzer>:</path/to/bin/>")

    return AnalyzerBinary(m.group("analyzer"), m.group("path"))
