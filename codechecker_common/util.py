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
import json
import portalocker

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
    iterator = iter(iterator)
    for first in iterator:
        rest_of_chunk = itertools.islice(iterator, 0, n - 1)
        yield itertools.chain([first], rest_of_chunk)


def load_json(path: str, default=None, lock=False, display_warning=True):
    """
    Load the contents of the given file as a JSON and return it's value,
    or default if the file can't be loaded.

    path -- JSON file path to load.
    defaut -- Value to return if JSON can't be loaded for some reason (e.g
              file doesn't exist, bad JSON format, etc.)
    lock -- Use portalocker to lock the JSON file for exclusive use.
    display_warning -- Display warning messages why the JSON file can't be
                       loaded (e.g. bad format, failed to open file, etc.)
    """

    ret = default
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
            if lock:
                portalocker.lock(handle, portalocker.LOCK_SH)

            ret = json.load(handle)

            if lock:
                portalocker.unlock(handle)
    except IOError as ex:
        if display_warning:
            LOG.warning("Failed to open json file: %s", path)
            LOG.warning(ex)
    except OSError as ex:
        if display_warning:
            LOG.warning("Failed to open json file: %s", path)
            LOG.warning(ex)
    except ValueError as ex:
        if display_warning:
            LOG.warning("%s is not a valid json file.", path)
            LOG.warning(ex)
    except TypeError as ex:
        if display_warning:
            LOG.warning('Failed to process json file: %s', path)
            LOG.warning(ex)

    return ret
