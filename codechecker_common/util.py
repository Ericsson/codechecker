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
import re
import shlex
import yaml
import os
import pathlib
from typing import List, TextIO

import portalocker

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def arg_match(options, args):
    """Checks and selects the option string specified in 'options'
    that are present in parameter 'args'."""
    matched_args = []
    for option in options:
        if any(arg if option.startswith(arg) else None for arg in args):
            matched_args.append(option)
            continue

    return matched_args


def clamp(min_: int, value: int, max_: int) -> int:
    """Clamps ``value`` such that ``min_ <= value <= max_``."""
    if min_ > max_:
        raise ValueError("min <= max required")
    return min(max(min_, value), max_)


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


def load_yaml(path: str):
    """
    Load the contents of the given file as a YAML and return it's value.
    """

    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as ex:
        LOG.warning("Failed to open YAML file: %s", path)
        LOG.warning(ex)
        return None
    except yaml.YAMLError as ex:
        LOG.warning("Failed to parse YAML file: %s", path)
        LOG.warning(ex)
        return None
    except ValueError as ex:
        LOG.warning("%s is not a valid YAML file.", path)
        LOG.warning(ex)
        return None
    except TypeError as ex:
        LOG.warning("Failed to process YAML file: %s", path)
        LOG.warning(ex)
        return None


def get_linef(fp: TextIO, line_no: int) -> str:
    """'fp' should be (readable) file object.
    Return the line content at line_no or an empty line
    if there is less lines than line_no.
    """
    fp.seek(0)
    for line in fp:
        line_no -= 1
        if line_no == 0:
            return line
    return ''


def path_for_fake_root(full_path: str, root_path: str = '/') -> str:
    """Normalize and sanitize full_path, then make it relative to root_path."""
    relative_path = os.path.relpath(full_path, '/')
    fake_root_path = os.path.join(root_path, relative_path)
    return os.path.abspath(fake_root_path)


def strtobool(value: str) -> bool:
    """Parse a string value to a boolean."""
    return value.lower() in ('y', 'yes', 't', 'true', 'on', '1')


def index_of(iterable, lambda_func) -> int:
    """Return the index of the first element in iterable for which
    lambda_func returns True.
    """
    for i, item in enumerate(iterable):
        if lambda_func(item):
            return i

    return -1


def replace_env_var(cfg_file):
    """
    Returns a replacement function which can be used in RegEx functions such as
    re.sub to replace matches with a string from the OS environment.
    """
    def replacer(matchobj):
        env_var = matchobj.group(1)
        if env_var not in os.environ:
            LOG.error('%s environment variable not set in %s', env_var,
                      cfg_file)
            return ''
        return os.environ[env_var]

    return replacer


def load_args_from_file(filepath: str) -> List[str]:
    """
    Returns the content of the given file as a list of command line arguments.
    The file may contain parts in $(this) format. These will be replaced by the
    environment variable with this given name.
    Throws FileNotFoundError if the file doesn't exist.
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = re.sub(
            r'\$\((.*?)\)',
            replace_env_var(filepath),
            f.read().strip())
        return shlex.split(content)


# TODO: This class is used for checking if a path exists. This class should
# inherit from pathlib.Path, however it is not possible before Python 3.12 due
# to a bug:
# https://stackoverflow.com/questions/61689391/error-with-simple-subclassing-
# of-pathlib-path-no-flavour-attribute
class ExistingPath:
    def __init__(self, *pathsegments):
        path = pathlib.Path(*pathsegments)

        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path.absolute()}")
