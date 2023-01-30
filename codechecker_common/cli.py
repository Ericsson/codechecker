# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Main CodeChecker script.
"""


import argparse
from importlib import machinery
import json
import os
import signal
import sys


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        """
        By default argparse will exit with error code 2 in case of error, but
        we are using this error code for different purposes. For this reason
        we will override this function, so we will exit with error code 1 in
        such cases too.
        """
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def add_subcommand(subparsers, sub_cmd, cmd_module_path, lib_dir_path):
    """
    Load the subcommand module and then add the subcommand to the available
    subcommands in the given subparsers collection.

    subparsers has to be the return value of the add_parsers() method on an
    argparse.ArgumentParser.
    """
    m_path, m_name = os.path.split(cmd_module_path)

    module_name = os.path.splitext(m_name)[0]
    target = [os.path.join(lib_dir_path, m_path)]

    # Load the module named as the argument.
    cmd_spec = machinery.PathFinder().find_spec(module_name,
                                                target)
    command_module = cmd_spec.loader.load_module(module_name)

    # Now that the module is loaded, construct an ArgumentParser for it.
    sc_parser = subparsers.add_parser(
        sub_cmd, **command_module.get_argparser_ctor_args())

    # Run the method which adds the arguments to the subcommand's handler.
    command_module.add_arguments_to_parser(sc_parser)


def get_data_files_dir_path():
    """ Get data files directory path """
    bin_dir = os.environ.get('CC_BIN_DIR')

    # In case of internal package we return the parent directory of the 'bin'
    # folder.
    if bin_dir:
        return os.path.dirname(bin_dir)

    # If this is a pip-installed package, try to find the data directory.
    import sysconfig
    data_dir_paths = [
        # Try to find the data directory beside the lib directory.
        # /usr/local/lib/python3.8/dist-packages/codechecker_common/cli.py
        # (this file) -> /usr/local
        os.path.abspath(os.path.join(__file__, *[os.path.pardir] * 5)),

        # Automatically try to find data directory if it can be found in
        # standard locations.
        *set(sysconfig.get_path("data", s)
             for s in sysconfig.get_scheme_names())]

    for dir_path in data_dir_paths:
        data_dir_path = os.path.join(dir_path, 'share', 'codechecker')
        if os.path.exists(data_dir_path):
            return data_dir_path

    print("Failed to get CodeChecker data files directory path in: ",
          data_dir_paths)
    sys.exit(1)


def main():
    """
    CodeChecker main command line.
    """
    if not os.environ.get('CC_LIB_DIR'):
        os.environ['CC_LIB_DIR'] = \
                os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    data_files_dir_path = get_data_files_dir_path()
    os.environ['CC_DATA_FILES_DIR'] = data_files_dir_path

    # Load the available CodeChecker subcommands.
    # This list is generated dynamically by scripts/build_package.py, and is
    # always meant to be available alongside the CodeChecker.py.
    commands_cfg = os.path.join(data_files_dir_path, "config", "commands.json")

    with open(commands_cfg, encoding="utf-8", errors="ignore") as cfg_file:
        subcommands = json.load(cfg_file)

    def signal_handler(signum, frame):
        """
        Without this handler the PostgreSQL
        server does not terminate at signal.
        """
        sys.exit(128 + signum)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        parser = ArgumentParser(
            prog="CodeChecker",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""Run the CodeChecker sourcecode analyzer framework.
Please specify a subcommand to access individual features.""",
            epilog="""Example scenario: Analyzing, and storing results
------------------------------------------------
Start the server where the results will be stored and can be viewed
after the analysis is done:
    CodeChecker server

Analyze a project with default settings:
    CodeChecker check -b "cd ~/myproject && make" -o "~/results"

Store the analyzer results to the server:
    CodeChecker store "~/results" -n myproject

The results can be viewed:
 * In a web browser: http://localhost:8001
 * In the command line:
    CodeChecker cmd results myproject

Example scenario: Analyzing, and printing results to Terminal (no storage)
--------------------------------------------------------------------------
In this case, no database is used, and the results are printed on the standard
output.

    CodeChecker check -b "cd ~/myproject && make\" """)

        subparsers = parser.add_subparsers(help='commands')

        if subcommands:
            # Try to check if the user has already given us a subcommand to
            # execute. If so, don't load every available parts of CodeChecker
            # to ensure a more optimised run.
            if len(sys.argv) > 1:
                first_command = sys.argv[1]
                if first_command in subcommands:

                    # Consider only the given command as an available one.
                    subcommands = {first_command: subcommands[first_command]}

            lib_dir_path = os.environ.get('CC_LIB_DIR')
            for subcommand in subcommands:
                try:
                    add_subcommand(subparsers, subcommand,
                                   subcommands[subcommand], lib_dir_path)
                except (IOError, ImportError):
                    print("Couldn't import module for subcommand '" +
                          subcommand + "'... ignoring.")
                    import traceback
                    traceback.print_exc(file=sys.stdout)

        args = parser.parse_args()

        # Call handler function to process configuration files. If there are
        # any configuration options available in one of the given file than
        # extend the system argument list with these options and try to parse
        # the argument list again to validate it.
        if 'func_process_config_file' in args:
            # Import logger module here after 'CC_DATA_FILES_DIR' environment
            # variable is set, so 'setup_logger' will be able to initialize
            # the logger properly.
            from codechecker_common import logger
            logger.setup_logger(
                args.verbose if 'verbose' in args else None,
                'stderr')
            LOG = logger.get_logger('system')

            if len(sys.argv) > 1:
                called_sub_command = sys.argv[1]

            cfg_args = args.func_process_config_file(args, called_sub_command)
            if cfg_args:
                # Expand environment variables in the arguments.
                cfg_args = [os.path.expandvars(cfg) for cfg in cfg_args]

                # Replace --config option with the options inside the config
                # file.
                cfg_idx = sys.argv.index("--config")
                sys.argv = sys.argv[:cfg_idx] + cfg_args + \
                    sys.argv[cfg_idx + 2:]

                args = parser.parse_args()
                LOG.info("Full extended command: %s", ' '.join(sys.argv))

        if 'func' in args:
            sys.exit(args.func(args))
        else:
            # Print the help message of the current command if no subcommand
            # is given.
            sys.argv.append("--help")
            args = parser.parse_args()
            args.func(args)

    except KeyboardInterrupt as kb_err:
        print(str(kb_err))
        print("Interrupted by user...")
        sys.exit(1)

    # Handle all exception, but print stacktrace. It is needed for atexit.
    # atexit does not work correctly when an unhandled exception occurred.
    # So in this case, the servers left running when the script exited.
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
