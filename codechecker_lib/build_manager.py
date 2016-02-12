# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
build and log related stuff
"""
import os
import sys
import pickle
import subprocess

from codechecker_lib import logger
from codechecker_lib import analyzer_env

LOG = logger.get_new_logger('BUILD MANAGER')


def perform_build_command(logfile, command, context, silent=False):
    """
    Build the project and create a log file.
    """
    if not silent:
        LOG.info("Starting build ...")

    try:
        original_env_file = os.environ['CODECHECKER_ORIGINAL_BUILD_ENV']
        LOG.debug('Loading original build env from: ' + original_env_file)

        with open(original_env_file, 'rb') as env_file:
            original_env = pickle.load(env_file)

    except Exception as ex:
        LOG.warning(str(ex))
        LOG.warning('Failed to get saved original_env using a current copy for logging')
        original_env = os.environ.copy()

    return_code = 0
    # Run user's commands in shell
    log_env = analyzer_env.get_log_env(logfile, context, original_env)

    if 'CC_LOGGER_GCC_LIKE' not in log_env:
      log_env['CC_LOGGER_GCC_LIKE'] = 'gcc:g++:clang:clang++:cc:c++'

    LOG.debug(log_env)
    try:
        proc = subprocess.Popen(command,
                                bufsize=-1,
                                env=log_env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                shell=True)
        while True:
            line = proc.stdout.readline()
            if not silent:
                print line,
            if line == '' and proc.poll() is not None:
                break

        return_code = proc.returncode

        if not silent:
            if return_code == 0:
                LOG.info("Build finished successfully.")
                LOG.debug("The logfile is: " + logfile)
            else:
                LOG.info("Build failed.")
                sys.exit(1)
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
            LOG.debug("Compilation database file does not exists.")
            return None
    except AttributeError as ex:
        # args.log_file was not set
        LOG.debug(ex)
        LOG.debug("Compilation database file was not set in the command line.")
    finally:
        return log_file


def generate_log_file(args, context, silent=False):
    """
    Returns a build command log file for check/quickcheck command.
    """

    log_file = None
    try:
        if args.command:
            # check if logger bin exists
            if not os.path.isfile(context.path_logger_bin):
                LOG.debug('Logger binary not found! Required for logging.')
                sys.exit(1)

            # check if logger lib exists
            if not os.path.exists(context.path_logger_lib):
                LOG.debug('Logger library directory not found! Libs are requires' \
                          'for logging.')
                sys.exit(1)

            log_file = default_compilation_db(args.workspace)
            if os.path.exists(log_file):
                LOG.debug("Removing previous compilation command file: " +
                          log_file)
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
