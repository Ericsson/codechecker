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


def add_subcommand(subparsers, sub_cmd, cmd_module_path):
    """
    Load the subcommand module and then add the subcommand to the available
    subcommands in the given subparsers collection.

    subparsers has to be the return value of the add_parsers() method on an
    argparse.ArgumentParser.
    """
    m_path, m_name = os.path.split(cmd_module_path)
    module_name = os.path.splitext(m_name)[0]

    cc_bin = os.path.dirname(os.path.realpath(__file__))
    full_module_path = os.path.join(cc_bin, '..', 'lib', 'python3', m_path)

    # Load the module named as the argument.
    cmd_spec = machinery.PathFinder().find_spec(module_name,
                                                [full_module_path])
    command_module = cmd_spec.loader.load_module(module_name)

    # Now that the module is loaded, construct an ArgumentParser for it.
    sc_parser = subparsers.add_parser(
        sub_cmd, **command_module.get_argparser_ctor_args())

    # Run the method which adds the arguments to the subcommand's handler.
    command_module.add_arguments_to_parser(sc_parser)


def main(subcommands=None):
    """
    CodeChecker main command line.
    """

    def signal_handler(signum, frame):
        """
        Without this handler the PostgreSQL
        server does not terminate at signal.
        """
        sys.exit(128 + signum)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        parser = argparse.ArgumentParser(
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

            for subcommand in subcommands:
                try:
                    add_subcommand(subparsers, subcommand,
                                   subcommands[subcommand])
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

        if 'func' in args:
            args.func(args)
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

    # Load the available CodeChecker subcommands.
    # This list is generated dynamically by scripts/build_package.py, and is
    # always meant to be available alongside the CodeChecker.py.
    commands_cfg = os.path.join(os.path.dirname(__file__), "commands.json")

    with open(commands_cfg, encoding="utf-8", errors="ignore") as cfg_file:
        commands = json.load(cfg_file)

    main(commands)
