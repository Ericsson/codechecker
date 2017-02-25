# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
""""""

import os

from codechecker_lib.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('ENV')


# -----------------------------------------------------------------------------
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
    except:
        new_env['LD_LIBRARY_PATH'] = context.path_logger_lib

    # Set ld logger logfile.
    new_env[context.env_var_cc_logger_file] = logfile

    return new_env


# -----------------------------------------------------------------------------
def get_check_env(path_env_extra, ld_lib_path_extra):
    """
    Extending the checker environment.
    Check environment is extended to find tools if they ar not on
    the default places.
    """
    new_env = os.environ.copy()

    if len(path_env_extra) > 0:
        extra_path = ':'.join(path_env_extra)
        LOG.debug_analyzer(
            'Extending PATH environment variable with: ' + extra_path)

        try:
            new_env['PATH'] = extra_path + ':' + new_env['PATH']
        except:
            new_env['PATH'] = extra_path

    if len(ld_lib_path_extra) > 0:
        extra_lib = ':'.join(ld_lib_path_extra)
        LOG.debug_analyzer(
            'Extending LD_LIBRARY_PATH environment variable with: ' +
            extra_lib)
        try:
            original_ld_library_path = new_env['LD_LIBRARY_PATH']
            new_env['LD_LIBRARY_PATH'] = \
                extra_lib + ':' + original_ld_library_path
        except:
            new_env['LD_LIBRARY_PATH'] = extra_lib

    return new_env
