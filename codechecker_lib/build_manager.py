# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
build and log related stuff
"""
import os
import pickle
import subprocess
import sys
import shutil
import platform

from codechecker_lib import logger
from codechecker_lib import analyzer_env
from codechecker_lib import host_check

from distutils.spawn import find_executable

LOG = logger.get_new_logger('BUILD MANAGER')


def execute_buildcmd(command, silent=False, env=None, cwd=None):
    """
    Execute the the build command and continously write
    the output from the process to the standard output.
    """
    proc = subprocess.Popen(command,
                            bufsize=-1,
                            env=env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            cwd=cwd,
                            shell=True)

    while True:
        line = proc.stdout.readline()
        if not silent:
            sys.stdout.write(line)
        if line == '' and proc.poll() is not None:
            break

    return proc.returncode


def perform_build_command(logfile, command, context, silent=False):
    """
    Build the project and create a log file.
    """
    if not silent:
        LOG.info("Starting build ...")

    try:
        original_env_file = os.environ['CODECHECKER_ORIGINAL_BUILD_ENV']
        LOG.debug_analyzer('Loading original build env from: ' +
                           original_env_file)

        with open(original_env_file, 'rb') as env_file:
            original_env = pickle.load(env_file)

    except Exception as ex:
        LOG.warning(str(ex))
        LOG.warning('Failed to get saved original_env'
                    'using a current copy for logging')
        original_env = os.environ.copy()

    return_code = 0

    # Run user's commands with intercept
    if host_check.check_intercept(original_env):
        LOG.debug_analyzer("with intercept ...")
        final_command = command
        command = "intercept-build " + "--cdb " + logfile + " " + final_command
        log_env = original_env
        LOG.debug_analyzer(command)

    # Run user's commands in shell
    else:
        # TODO better platform detection
        if platform.system() == 'Linux':
            LOG.debug_analyzer("with ld logger ...")
            log_env = analyzer_env.get_log_env(logfile, context, original_env)
            if 'CC_LOGGER_GCC_LIKE' not in log_env:
                log_env['CC_LOGGER_GCC_LIKE'] = 'gcc:g++:clang:clang++:cc:c++'
        else:
            LOG.error("Intercept-build is required"
                      " to run CodeChecker in OS X.")
            sys.exit(1)

    LOG.debug_analyzer(log_env)
    try:
        ret_code = execute_buildcmd(command, silent, log_env)

        if not silent:
            if ret_code == 0:
                LOG.info("Build finished successfully.")
                LOG.debug_analyzer("The logfile is: " + logfile)
            else:
                LOG.info("Build failed.")
                sys.exit(ret_code)

    except Exception as ex:
        LOG.error("Calling original build command failed")
        LOG.error(str(ex))
        sys.exit(1)


def default_compilation_db(workspace_path):
    """
    default compilation commands database file in the workspace
    """
    compilation_commands = os.path.join(workspace_path,
                                        'compilation_commands.json')
    return compilation_commands


def check_log_file(args):
    """
    check if the compilation command file was set in the command line
    if not check if it is in the workspace directory
    """
    log_file = None
    try:
        if args.logfile:
            log_file = os.path.realpath(args.logfile)
        else:
            # log file could be in the workspace directory
            log_file = default_compilation_db(args.workspace)
        if not os.path.exists(log_file):
            LOG.debug_analyzer("Compilation database file does not exists.")
            return None
    except AttributeError as ex:
        # args.log_file was not set
        LOG.debug_analyzer(ex)
        LOG.debug_analyzer("Compilation database file was not set"
                           " in the command line.")
    finally:
        return log_file


def generate_log_file(args, context, silent=False):
    """
    Returns a build command log file for check/quickcheck command.
    """

    log_file = None
    try:
        if args.command:

            intercept_build_executable = find_executable('intercept-build')

            if intercept_build_executable is None:
                if platform.system() == 'Linux':
                    # check if logger bin exists
                    if not os.path.isfile(context.path_logger_bin):
                        LOG.error('Logger binary not found!'
                                  'Required for logging.')
                        sys.exit(1)

                    # check if logger lib exists
                    if not os.path.exists(context.path_logger_lib):
                        LOG.error('Logger library directory not found!'
                                  'Libs are required for logging.')
                        sys.exit(1)

            log_file = default_compilation_db(args.workspace)
            if os.path.exists(log_file):
                LOG.debug_analyzer("Removing previous"
                                   "compilation command file: " + log_file)
                os.remove(log_file)

            open(log_file, 'a').close()  # same as linux's touch

            perform_build_command(log_file,
                                  args.command,
                                  context,
                                  silent=silent)

    except AttributeError as aerr:
        LOG.error(aerr)
        sys.exit(1)

    return log_file
