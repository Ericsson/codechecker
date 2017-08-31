# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""
Main CodeChecker script.
"""
from __future__ import print_function

import argparse
import json
import os
import signal
import sys

from shared.ttypes import RequestFailed

from libcodechecker import libhandlers
from libcodechecker.logger import LoggerFactory


LOG = LoggerFactory.get_new_logger('MAIN')


def main(subcommands=None):
    """
    CodeChecker main command line.
    """

    def signal_handler(sig, frame):
        """
        Without this handler the PostgreSQL
        server does not terminate at signal.
        """
        sys.exit(1)

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
    CodeChecker check -b "cd ~/myproject && make" -n myproject

The results can be viewed:
 * In a web browser: http://localhost:8001
 * In the command line:
    CodeChecker cmd results -n myproject

Example scenario: Analyzing, and printing results to Terminal (no storage)
--------------------------------------------------------------------------
In this case, no database is used, and the results are printed on the standard
output.

    CodeChecker quickcheck -b "cd ~/myproject && make\"""")

        subparsers = parser.add_subparsers(help='commands')

        if subcommands:
            # Try to check if the user has already given us a subcommand to
            # execute. If so, don't load every available parts of CodeChecker
            # to ensure a more optimised run.
            if len(sys.argv) > 1:
                first_command = sys.argv[1]
                if first_command in subcommands:
                    LOG.debug("Supplied an existing, valid subcommand: " +
                              first_command)

                    # Consider only the given command as an available one.
                    subcommands = [first_command]

            for subcommand in subcommands:
                LOG.debug("Creating arg parser for subcommand " + subcommand)

                try:
                    libhandlers.add_subcommand(subparsers, str(subcommand))
                except (IOError, ImportError):
                    LOG.warning("Couldn't import module for subcommand '" +
                                subcommand + "'... ignoring.")
                    import traceback
                    traceback.print_exc(file=sys.stdout)

        args = parser.parse_args()
        if 'verbose' in args:
            LoggerFactory.set_log_level(args.verbose)
        args.func(args)

    except KeyboardInterrupt as kb_err:
        LOG.info(str(kb_err))
        LOG.info("Interrupted by user...")
        sys.exit(1)

    except RequestFailed as thrift_ex:
        LOG.info("Server error.")
        LOG.info("Error code: " + str(thrift_ex.errorCode))
        LOG.info("Error message: " + str(thrift_ex.message))
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
    LOG.debug(sys.path)
    LOG.debug(sys.version)
    LOG.debug(sys.executable)
    LOG.debug(os.environ.get('LD_LIBRARY_PATH'))

    # Load the available CodeChecker subcommands.
    # This list is generated dynamically by scripts/build_package.py, and is
    # always meant to be available alongside the CodeChecker.py.
    commands_cfg = os.path.join(os.path.dirname(__file__), "commands.json")

    with open(commands_cfg) as cfg_file:
        commands = json.load(cfg_file)

    LOG.debug("Available CodeChecker subcommands: ")
    LOG.debug(commands)

    main(commands)
