# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""""""


import os
import re

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def get_log_env(logfile, context, original_env):
    """
    Environment for logging. With the ld logger.
    Keep the original environment unmodified as possible.
    Only environment variables required for logging are changed.
    """
    new_env = original_env

    new_env[context.env_var_cc_logger_bin] = context.path_logger_bin

    new_env['LD_PRELOAD'] = context.logger_lib_name

    try:
        original_ld_library_path = new_env['LD_LIBRARY_PATH']
        new_env['LD_LIBRARY_PATH'] = context.path_logger_lib + ':' + \
            original_ld_library_path
    except KeyError:
        new_env['LD_LIBRARY_PATH'] = context.path_logger_lib

    # Set ld logger logfile.
    new_env[context.env_var_cc_logger_file] = logfile

    return new_env


def extend(path_env_extra, ld_lib_path_extra):
    """Extend the checker environment.

    The default environment is extended with the given PATH and
    LD_LIBRARY_PATH values to find tools if they ar not on
    the default places.
    """
    new_env = os.environ.copy()

    if path_env_extra:
        extra_path = ':'.join(path_env_extra)
        LOG.debug_analyzer(
            'Extending PATH environment variable with: ' + extra_path)

        try:
            new_env['PATH'] = extra_path + ':' + new_env['PATH']
        except KeyError:
            new_env['PATH'] = extra_path

    if ld_lib_path_extra:
        extra_lib = ':'.join(ld_lib_path_extra)
        LOG.debug_analyzer(
            'Extending LD_LIBRARY_PATH environment variable with: ' +
            extra_lib)
        try:
            original_ld_library_path = new_env['LD_LIBRARY_PATH']
            new_env['LD_LIBRARY_PATH'] = \
                extra_lib + ':' + original_ld_library_path
        except KeyError:
            new_env['LD_LIBRARY_PATH'] = extra_lib

    return new_env


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


def find_by_regex_in_envpath(pattern, environment):
    """
    Searches for files matching the pattern string in the environment's PATH.
    """

    regex = re.compile(pattern)

    binaries = {}
    for path in environment['PATH'].split(os.pathsep):
        _, _, filenames = next(os.walk(path), ([], [], []))
        for f in filenames:
            if re.match(regex, f):
                if binaries.get(f) is None:
                    binaries[f] = [os.path.join(path, f)]
                else:
                    binaries[f].append(os.path.join(path, f))

    return binaries


def get_binary_in_path(basename_list, versioning_pattern, env):
    """
    Select the most matching binary for the given pattern in the given
    environment. Works well for binaries that contain versioning.
    """

    binaries = find_by_regex_in_envpath(versioning_pattern, env)

    if not binaries:
        return False
    elif len(binaries) == 1:
        # Return the first found (earliest in PATH) binary for the only
        # found binary name group.
        return list(binaries.values())[0][0]
    else:
        keys = list(binaries.keys())
        keys.sort()

        # If one of the base names match, select that version.
        files = None
        for base_key in basename_list:
            # Cannot use set here as it would destroy precendence.
            if base_key in keys:
                files = binaries[base_key]
                break

        if not files:
            # Select the "newest" available version if there are multiple and
            # none of the base names matched.
            files = binaries[keys[-1]]

        # Return the one earliest in PATH.
        return files[0]


def is_analyzer_from_path():
    """ Return True if CC_ANALYZERS_FROM_PATH environment variable is set. """
    analyzers_from_path = os.environ.get('CC_ANALYZERS_FROM_PATH', '').lower()
    if analyzers_from_path in ['yes', '1']:
        return True
    return False


def get_clangsa_plugin_dir():
    """ Return the value of the CC_CLANGSA_PLUGIN_DIR environment variable. """
    return os.environ.get('CC_CLANGSA_PLUGIN_DIR')
