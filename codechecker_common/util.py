# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Util module.
"""


import itertools

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def arg_match(options, args):
    """Checks and selects the option string specified in 'options'
    that are present in parameter 'args'."""
    matched_args = []
    for option in options:
        if any([arg if option.startswith(arg) else None
                for arg in args]):
            matched_args.append(option)
            continue

    return matched_args


def chunks(iterator, n):
    """
    Yield the next chunk if an iterable object. A chunk consists of maximum n
    elements.
    """
    for first in iterator:
        rest_of_chunk = itertools.islice(iterator, 0, n - 1)
        yield itertools.chain([first], rest_of_chunk)
