# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Implements the old command "CodeChecker plist", a branching wrapper over the
functionality of 'store' and 'parse'.
"""

import argparse
import os
import sys

from libcodechecker import libhandlers
from libcodechecker import util
from libcodechecker.logger import add_verbose_arguments
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('PLIST')


class OrderedCheckersAction(argparse.Action):
    """
    Action to store enabled and disabled checkers
    and keep ordering from command line.

    Create separate lists based on the checker names for
    each analyzer.
    """

    # Users can supply invocation to 'codechecker-analyze' as follows:
    # -e core -d core.uninitialized -e core.uninitialized.Assign
    # We must support having multiple '-e' and '-d' options and the order
    # specified must be kept when the list of checkers are assembled for Clang.

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(OrderedCheckersAction, self).__init__(option_strings, dest,
                                                    **kwargs)

    def __call__(self, parser, namespace, value, option_string=None):

        if 'ordered_checkers' not in namespace:
            namespace.ordered_checkers = []
        ordered_checkers = namespace.ordered_checkers
        ordered_checkers.append((value, self.dest == 'enable'))

        namespace.ordered_checkers = ordered_checkers


class DeprecatedOptionAction(argparse.Action):
    """
    Deprecated argument action.
    """

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=0,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None,
                 kill_if_used=False,
                 error_string=None):
        super(DeprecatedOptionAction, self). \
            __init__(option_strings,
                     dest,
                     const='deprecated_option',
                     default=argparse.SUPPRESS,
                     type=None,
                     nargs=nargs,
                     choices=None,
                     required=False,
                     help="(Usage of this argument is DEPRECATED and has no "
                          "effect!)",
                     metavar='')
        self.__error_string = error_string
        self.__kill_if_used = kill_if_used

    def __call__(self, parser, namespace, value=None, option_string=None):
        if not self.__error_string:
            LOG.warning("Deprecated command line option used: '" +
                        option_string + "'")
        else:
            LOG.warning(self.__error_string)

        if self.__kill_if_used:
            setattr(namespace, '_deprecated', True)


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker plist',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Parse plist files in the given directory and "
                       "store the defects found therein to the database "
                       "or print to the standard output.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Use plist files in a given directory to pretty-print or "
                "store the results."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    # TODO: --name does not exist in 'parse'.
    # In 'store', --name is not a required argument by argparse, as 'analyze'
    # can prepare a name, which is read after 'store' is started.
    # If the name is missing, the user is explicitly warned.
    # TODO: This should be an optional argument here too. Also it doesn't make
    # sense to require --name if --stdout ('parse'-mode) is set.
    parser.add_argument('-n', '--name',
                        type=str,
                        dest="name",
                        required=True,
                        default=argparse.SUPPRESS,
                        help="The name of the analysis run to use in storing "
                             "the reports to the database. If not specified, "
                             "the '--name' parameter given to 'codechecker-"
                             "analyze' will be used, if exists.")

    # TODO: This argument is without an opt-string in 'store' and 'parse'.
    parser.add_argument('-d', '--directory',
                        type=str,
                        dest="directory",
                        required=True,
                        help="Path of the directory where the plist files "
                             "to be used are found.")

    # TODO: Workspace is no longer a concept in the new subcommands.
    parser.add_argument('-w', '--workspace',
                        type=str,
                        default=util.get_default_workspace(),
                        dest="workspace",
                        help="Directory where CodeChecker can store analysis "
                             "related data, such as the database.")

    parser.add_argument('-f', '--force',
                        dest="force",
                        default=False,
                        action='store_true',
                        required=False,
                        help="Delete analysis results stored in the database "
                             "for the current analysis run's name and store "
                             "only the results reported in the 'input' files. "
                             "(By default, CodeChecker would keep reports "
                             "that were coming from files not affected by the "
                             "analysis, and only incrementally update defect "
                             "reports for source files that were analysed.)")

    parser.add_argument('-j', '--jobs',
                        type=int,
                        dest="jobs",
                        required=False,
                        default=1,
                        help="Number of threads to use in parsing and storing "
                             "of results. More threads mean faster analysis "
                             "at the cost of using more memory.")

    # TODO: Parse does not know '-s' or '--steps' for this.
    parser.add_argument('-s', '--steps', '--print-steps',
                        dest="print_steps",
                        action="store_true",
                        required=False,
                        help="Print the steps the analyzers took in finding "
                             "the reported defect.")

    parser.add_argument('--stdout',
                        dest="stdout",
                        action='store_true',
                        required=False,
                        default=False,
                        help="Print the analysis results to the standard "
                             "output instead of storing to the database.")

    server_args = parser.add_argument_group(
        "server arguments",
        "Specifies a 'CodeChecker server' instance which will be used to "
        "store the results. This server must be running and listening prior "
        "to the 'store' command being ran.")

    server_args.add_argument('--host',
                             type=str,
                             dest="host",
                             required=False,
                             default="localhost",
                             help="The IP address or hostname of the "
                                  "CodeChecker server.")

    server_args.add_argument('-p', '--port',
                             type=int,
                             dest="port",
                             required=False,
                             default=8001,
                             help="The port of the server to use for storing.")

    # TODO: These arguments have been retroactively removed from 'store'
    # and are deprecated here. They should be completely removed.
    dbmodes = parser.add_argument_group("database arguments")
    dbmodes = dbmodes.add_mutually_exclusive_group(required=False)
    db_deprec = "Database connectivity has been removed from 'check'. " \
                "Please specify a CodeChecker server address via --host " \
                "and --port instead!"

    # SQLite is the default, and for 'check', it was deprecated.
    # TODO: In 'store', --sqlite has been replaced as an option to specify the
    # .sqlite file, essentially replacing the concept of 'workspace'.
    dbmodes.add_argument('--sqlite',
                         kill_if_used=True,
                         error_string=db_deprec,
                         action=DeprecatedOptionAction)

    dbmodes.add_argument('--postgresql',
                         kill_if_used=True,
                         error_string=db_deprec,
                         action=DeprecatedOptionAction)

    pgsql = parser.add_argument_group("PostgreSQL arguments",
                                      "Values of these arguments are ignored, "
                                      "unless '--postgresql' is specified!")

    # WARNING: '--dbaddress' default value influences workspace creation
    # in SQLite.
    # TODO: These are '--db-something' in 'store', not '--dbsomething'.
    pgsql.add_argument('--dbaddress',
                       nargs=1,
                       kill_if_used=True,
                       error_string=db_deprec,
                       action=DeprecatedOptionAction)

    pgsql.add_argument('--dbport',
                       nargs=1,
                       kill_if_used=True,
                       error_string=db_deprec,
                       action=DeprecatedOptionAction)

    pgsql.add_argument('--dbusername',
                       nargs=1,
                       kill_if_used=True,
                       error_string=db_deprec,
                       action=DeprecatedOptionAction)

    pgsql.add_argument('--dbname',
                       nargs=1,
                       kill_if_used=True,
                       error_string=db_deprec,
                       action=DeprecatedOptionAction)

    add_verbose_arguments(parser)

    def __kill_deprec(args):
        if '_deprecated' in args:
            LOG.warning("A deprecated argument was passed to the "
                        "commandline. This argument has no effect anymore, "
                        "and the behaviour has changed.")
            LOG.error("Execution halted: CodeChecker would work in an "
                      "unexpected way with this argument passed.")
            sys.exit(2)  # argparse kills with error code 2.

        # Call the main process if everything matches.
        main(args)

    parser.set_defaults(func=__kill_deprec)


def main(args):
    """
    Execute a wrapper over 'parse' or 'store'.
    """

    def __load_module(name):
        """Loads the given subcommand's definition from the libs."""
        try:
            module = libhandlers.load_module(name)
        except ImportError:
            LOG.error("Couldn't import subcommand '" + name + "'.")
            raise

        return module

    def __update_if_key_exists(source, target, key):
        """Append the source Namespace's element with 'key' to target with
        the same key, but only if it exists."""
        if key in source:
            setattr(target, key, getattr(source, key))

    try:
        if args.stdout:
            # --- Parse mode ---
            parse_args = argparse.Namespace(
                input=[args.directory],
                print_steps=args.print_steps
            )

            parse_module = __load_module("parse")
            __update_if_key_exists(args, parse_args, "verbose")

            LOG.debug("Calling PARSE with args:")
            LOG.debug(parse_args)
            parse_module.main(parse_args)
        else:
            # --- Store mode ---
            workspace = os.path.abspath(args.workspace)
            if not os.path.isdir(workspace):
                os.makedirs(workspace)

            store_args = argparse.Namespace(
                input=[args.directory],
                input_format='plist',
                jobs=args.jobs,
                force=args.force,
                host=args.host,
                port=args.port
            )
            # Some arguments don't have default values.
            # We can't set these keys to None because it would result in an
            # error after the call.
            if 'postgresql' in args:
                __update_if_key_exists(args, store_args, 'postgresql')
            else:
                # If we are saving to a SQLite database, the wrapped 'check'
                # command used to do it in the workspace folder.
                setattr(store_args, 'sqlite',
                        os.path.join(workspace, 'codechecker.sqlite'))
            args_to_update = ['name']
            for key in args_to_update:
                __update_if_key_exists(args, store_args, key)

            store_module = __load_module("store")
            __update_if_key_exists(args, store_args, "verbose")

            LOG.debug("Calling STORE with args:")
            LOG.debug(store_args)
            store_module.main(store_args)

            # Show a hint for server start.
            LOG.info("To view results, open the CodeChecker server "
                     "'http://{0}:{1}' in your browser".format(args.host,
                                                               args.port))
    except ImportError:
        LOG.error("Check failed: couldn't import a library.")
    except Exception as ex:
        LOG.error("Running check failed. " + ex.message)
