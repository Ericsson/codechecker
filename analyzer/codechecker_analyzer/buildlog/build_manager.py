# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Build and log related functionality.
"""


import os
import pickle
import platform
import shlex
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
    proc = subprocess.Popen(
        command,
        bufsize=-1,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        shell=True,
        universal_newlines=True,
        encoding="utf-8",
        errors="ignore")

    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if not silent:
            sys.stdout.write(line)

    return proc.returncode


def perform_build_command(logfile, command, context, keep_link, silent=False,
                          verbose=None):
    """
    Build the project and create a log file.
    """
    LOG.info("Starting build...")

    original_env = os.environ
    try:
        original_env_file = os.environ.get('CODECHECKER_ORIGINAL_BUILD_ENV')
        if original_env_file:
            LOG.debug_analyzer('Loading original build env from: %s',
                               original_env_file)

            with open(original_env_file, 'rb') as env_file:
                original_env = pickle.load(env_file, encoding='utf-8')

    except Exception as ex:
        LOG.warning(str(ex))
        LOG.warning('Failed to get saved original_env '
                    'using a current copy for logging.')
        original_env = os.environ.copy()

    # Run user's commands in shell, and preload ldlogger.
    # TODO: better platform detection.
    if host_check.check_ldlogger(os.environ) and platform.system() == 'Linux':
        LOG.info("Using CodeChecker ld-logger.")

        # Same as linux's touch.
        open(logfile, 'a', encoding="utf-8", errors="ignore").close()
        log_env = env.get_log_env(logfile, context, original_env)
        if 'CC_LOGGER_GCC_LIKE' not in log_env:
            log_env['CC_LOGGER_GCC_LIKE'] = 'gcc:g++:clang:clang++:cc:c++'
        if keep_link or ('CC_LOGGER_KEEP_LINK' in log_env and
                         log_env['CC_LOGGER_KEEP_LINK'] == 'true'):
            log_env['CC_LOGGER_KEEP_LINK'] = 'true'

        is_debug = verbose and verbose in ['debug', 'debug_analyzer']
        if not is_debug and 'CC_LOGGER_DEBUG_FILE' in log_env:
            del log_env['CC_LOGGER_DEBUG_FILE']
        elif is_debug and 'CC_LOGGER_DEBUG_FILE' not in log_env:
            if 'CC_LOGGER_DEBUG_FILE' in os.environ:
                log_file = os.environ['CC_LOGGER_DEBUG_FILE']
            else:
                log_file = os.path.join(os.path.dirname(logfile),
                                        'codechecker.logger.debug')

            if os.path.exists(log_file):
                os.remove(log_file)

            log_env['CC_LOGGER_DEBUG_FILE'] = log_file
    elif host_check.check_intercept(os.environ):
        LOG.info("Using intercept-build.")
        command = ' '.join(["intercept-build",
                            "--cdb", logfile,
                            "sh -c", shlex.quote(command)])
        log_env = original_env
        LOG.debug_analyzer(command)
    else:
        # Print a helpful diagnostic.
        if platform.system() == 'Linux':
            LOG.error("Both ldlogger and intercept-build are unavailable.\n"
                      "Try acquiring the compilation_commands.json in another "
                      "way.\n"
                      "Install ldlogger or intercept-build to proceed.")
            sys.exit(1)
        if platform.system() == 'Windows':
            LOG.error("This command is not supported on Windows. You can use "
                      "the following tools to generate a compilation "
                      "database: \n"
                      " - CMake (CMAKE_EXPORT_COMPILE_COMMANDS)\n"
                      " - compiledb (https://pypi.org/project/compiledb/)")
            sys.exit(1)
        if platform.system() == 'Darwin':
            LOG.error("Intercept-build is required to run CodeChecker in "
                      "OS X.")
            sys.exit(1)
        LOG.error("Unrecognized platform. Open a GitHub issue for further "
                  "guidance.")
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
        debug_file = log_env.get('CC_LOGGER_DEBUG_FILE')
        if debug_file:
            LOG.info("The debug log file is: %s", debug_file)

            debug_logfile_lock = debug_file + '.lock'
            if os.path.exists(debug_logfile_lock):
                os.remove(debug_logfile_lock)

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
