# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Argument parsing related helper classes and functions."""


import argparse


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
        super(OrderedCheckersAction, self).__init__(option_strings, dest,
                                                    **kwargs)

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
        super(OrderedConfigAction, self).__init__(option_strings, dest,
                                                  nargs, **kwargs)

    def __call__(self, parser, namespace, value, option_string=None):

        assert isinstance(value, list), \
               f"--analyzer-config or --checker-config value ({value}) is " \
               "not a list, but should be if nargs is not None!"

        if not hasattr(namespace, self.dest):
            setattr(namespace, self.dest, [])

        dest = getattr(namespace, self.dest)

        for flag in value:
            if flag in dest:
                dest.remove(flag)
            dest.append(flag)
