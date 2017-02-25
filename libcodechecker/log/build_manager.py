# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Build and log related functionality.
"""
import os
import pickle
import platform
import subprocess
import sys
from uuid import uuid4
from distutils.spawn import find_executable

from codechecker_lib import analyzer_env
from codechecker_lib import host_check
from codechecker_lib.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('BUILD MANAGER')


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
                    'using a current copy for logging.')
        original_env = os.environ.copy()

    # Run user's commands with intercept.
    if host_check.check_intercept(original_env):
        LOG.debug_analyzer("with intercept ...")
        final_command = command
        command = "intercept-build " + "--cdb " + logfile + " " + final_command
        log_env = original_env
        LOG.debug_analyzer(command)

    # Run user's commands in shell.
    else:
        # TODO: better platform detection.
        if platform.system() == 'Linux':
            LOG.debug_analyzer("with ld logger ...")
            open(logfile, 'a').close()  # Same as linux's touch.
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

        if ret_code == 0:
            LOG.info("Build finished successfully.")
            LOG.debug_analyzer("The logfile is: " + logfile)
        else:
            LOG.info("Build failed.")
            sys.exit(ret_code)

    except Exception as ex:
        LOG.error("Calling original build command failed.")
        LOG.error(str(ex))
        sys.exit(1)


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


def check_log_file(args, context):
    """
    Check if the compilation command file was set in the command line.
    If the argument is not set generate a new.
    """
    log_file = None
    set_in_cmdline = False
    try:
        log_file = os.path.realpath(args.logfile)
        if not os.path.exists(log_file):
            LOG.error("The given compilation database"
                      "file does not exists: " + log_file)
            log_file = None
        set_in_cmdline = True
    except AttributeError as ex:
        # args.log_file was not set.
        LOG.debug(ex)
        LOG.debug("Compilation database file was not set"
                  " in the command line.")
        log_file = generate_log_file(args, context, args.quiet_build)
    finally:
        return log_file, set_in_cmdline


def generate_log_file(args, context, silent=False):
    """
    Returns a build command log file.
    """

    log_file = None
    try:
        if args.command:

            intercept_build_executable = find_executable('intercept-build')

            if intercept_build_executable is None:
                if platform.system() == 'Linux':
                    # Check if logger bin exists.
                    if not os.path.isfile(context.path_logger_bin):
                        LOG.error('Logger binary not found!'
                                  'Required for logging.')
                        sys.exit(1)

                    # Check if logger lib exists.
                    if not os.path.exists(context.path_logger_lib):
                        LOG.error('Logger library directory not found!'
                                  'Libs are required for logging.')
                        sys.exit(1)

            log_file = default_compilation_db(args.workspace, args.name)
            open(log_file, 'a').close()  # Same as linux's touch.

            perform_build_command(log_file,
                                  args.command,
                                  context,
                                  silent=silent)

    except AttributeError as aerr:
        LOG.error("Missing build command.")
    finally:
        return log_file
