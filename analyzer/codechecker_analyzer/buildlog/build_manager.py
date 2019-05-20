# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Build and log related functionality.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import pickle
import platform
import subprocess
import sys
from uuid import uuid4

from codechecker_common.logger import get_logger

from .. import env
from . import host_check

LOG = get_logger('buildlogger')


def execute_buildcmd(command, silent=False, env=None, cwd=None):
    """
    Execute the the build command and continuously write
    the output from the process to the standard output.
    """
    proc = subprocess.Popen(command,
                            bufsize=-1,
                            env=env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            cwd=cwd,
                            shell=True,
                            universal_newlines=True)

    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if not silent:
            print(line)

    return proc.returncode


def perform_build_command(logfile, command, context, keep_link, silent=False):
    """
    Build the project and create a log file.
    """
    LOG.info("Starting build ...")

    try:
        original_env_file = os.environ['CODECHECKER_ORIGINAL_BUILD_ENV']
        LOG.debug_analyzer('Loading original build env from: %s',
                           original_env_file)

        with open(original_env_file, 'rb') as env_file:
            original_env = pickle.load(env_file)

    except Exception as ex:
        LOG.warning(str(ex))
        LOG.warning('Failed to get saved original_env'
                    'using a current copy for logging.')
        original_env = os.environ.copy()

    # Run user's commands with intercept.
    if host_check.check_intercept(original_env):
        LOG.debug_analyzer("with intercept ...")
        final_command = command
        command = ' '.join(["intercept-build",
                            "--cdb", logfile,
                            "sh -c \"" + final_command + "\""])
        log_env = original_env
        LOG.debug_analyzer(command)

    # Run user's commands in shell.
    else:
        # TODO: better platform detection.
        if platform.system() == 'Linux':
            LOG.debug_analyzer("with ld logger ...")
            open(logfile, 'a').close()  # Same as linux's touch.
            log_env = env.get_log_env(logfile, context, original_env)
            if 'CC_LOGGER_GCC_LIKE' not in log_env:
                log_env['CC_LOGGER_GCC_LIKE'] = 'gcc:g++:clang:clang++:cc:c++'
            if keep_link or ('CC_LOGGER_KEEP_LINK' in log_env and
                             log_env['CC_LOGGER_KEEP_LINK'] == 'true'):
                log_env['CC_LOGGER_KEEP_LINK'] = 'true'
        else:
            LOG.error("Intercept-build is required"
                      " to run CodeChecker in OS X.")
            sys.exit(1)

    LOG.debug_analyzer(log_env)
    try:
        ret_code = execute_buildcmd(command, silent, log_env)

        if ret_code == 0:
            LOG.info("Build finished successfully.")
            LOG.debug_analyzer("The logfile is: %s", logfile)
        else:
            LOG.info("Build failed.")
            sys.exit(ret_code)

    except Exception as ex:
        LOG.error("Calling original build command failed.")
        LOG.error(str(ex))
        sys.exit(1)
    finally:
        # Removing flock lock file.
        logfile_lock = logfile + '.lock'
        if os.path.exists(logfile_lock):
            os.remove(logfile_lock)


def default_compilation_db(workspace_path, run_name):
    """
    Default compilation commands database file in the workspace.
    """
    workspace_path = os.path.abspath(workspace_path)
    uid = str(uuid4())[:10]  # 10 chars should be unique enough
    cmp_json_filename = 'compilation_commands_' + run_name + '_' \
                        + uid + '.json'
    compilation_commands = os.path.join(workspace_path, cmp_json_filename)
    return compilation_commands
