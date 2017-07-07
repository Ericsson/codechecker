# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Check implements a wrapper over 'log' + 'analyze' + 'store', essentially
giving an easy way to perform analysis from a log command and print results to
stdout.
"""

import argparse
import os
import shutil

from libcodechecker import libhandlers
from libcodechecker import util
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.logger import add_verbose_arguments
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('CHECK')


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
                 metavar=None):
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

    def __call__(self, parser, namespace, value=None, option_string=None):
        LOG.warning("Deprecated command line option used: '" +
                    option_string + "'")


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker check',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Run analysis for a project with storing results "
                       "in the database. Check only needs a build command or "
                       "an already existing logfile and performs every step "
                       "of doing the analysis in batch.",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': "If you wish to reuse the logfile resulting from executing "
                  "the build, see 'codechecker-log'. To keep analysis "
                  "results for later, see and use 'codechecker-analyze'. "
                  "To store previously saved analysis results in a database, "
                  "see 'codechecker-store'. 'CodeChecker check' exposes a "
                  "wrapper calling these three commands in succession. Please "
                  "make sure your build command actually builds the files -- "
                  "it is advised to execute builds on empty trees, aka. after "
                  "a 'make clean', as CodeChecker only analyzes files that "
                  "had been used by the build system. Analysis results can be "
                  "viewed by starting a 'CodeChecker server' and connecting "
                  "to it from a Web browser, or via 'CodeChecker cmd'.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Perform analysis on a project and store results to database."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    # Some arguments were deprecated already in 'CodeChecker check'.
    parser.add_argument('--keep-tmp',
                        action=DeprecatedOptionAction)

    parser.add_argument('-c', '--clean',
                        action=DeprecatedOptionAction)

    parser.add_argument('--update',
                        action=DeprecatedOptionAction)

    # In 'store', --name is not a required argument by argparse, as 'analyze'
    # can prepare a name, which is read after 'store' is started.
    # If the name is missing, the user is explicitly warned.
    # TODO: This should be an optional argument here too.
    parser.add_argument('-n', '--name',
                        type=str,
                        dest="name",
                        required=True,
                        default=argparse.SUPPRESS,
                        help="The name of the analysis run to use in storing "
                             "the reports to the database. If not specified, "
                             "the '--name' parameter given to 'codechecker-"
                             "analyze' will be used, if exists.")

    # TODO: Workspace is no longer a concept in the new subcommands.
    parser.add_argument('-w', '--workspace',
                        type=str,
                        default=util.get_default_workspace(),
                        dest="workspace",
                        help="Directory where CodeChecker can store analysis "
                             "related data, such as intermediate result files "
                             "and the database.")

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

    log_args = parser.add_argument_group(
        "log arguments",
        "Specify how the build information database should be obtained. You "
        "need to specify either an already existing log file, or a build "
        "command which will be used to generate a log file on the fly.")

    log_args.add_argument('-q', '--quiet-build',
                          dest="quiet_build",
                          action='store_true',
                          default=False,
                          required=False,
                          help="Do not print the output of the build tool "
                               "into the output of this command.")

    log_args = log_args.add_mutually_exclusive_group(required=True)

    log_args.add_argument('-b', '--build',
                          type=str,
                          dest="command",
                          default=argparse.SUPPRESS,
                          required=False,
                          help="Execute and record a build command. Build "
                               "commands can be simple calls to 'g++' or "
                               "'clang++' or 'make', but a more complex "
                               "command, or the call of a custom script file "
                               "is also supported.")

    log_args.add_argument('-l', '--logfile',
                          type=str,
                          dest="logfile",
                          help="Use an already existing JSON compilation "
                               "command database file specified at this path.")

    analyzer_opts = parser.add_argument_group("analyzer arguments")
    analyzer_opts.add_argument('-j', '--jobs',
                               type=int,
                               dest="jobs",
                               required=False,
                               default=1,
                               help="Number of threads to use in analysis. "
                                    "More threads mean faster analysis at "
                                    "the cost of using more memory.")

    # TODO: Analyze knows '--ignore' also for this.
    analyzer_opts.add_argument('-i', '--skip',
                               dest="skipfile",
                               required=False,
                               default=argparse.SUPPRESS,
                               help="Path to the Skipfile dictating which "
                                    "project files should be omitted from "
                                    "analysis. Please consult the User guide "
                                    "on how a Skipfile should be laid out.")

    analyzer_opts.add_argument('--analyzers',
                               nargs='+',
                               dest='analyzers',
                               metavar='ANALYZER',
                               required=False,
                               choices=analyzer_types.supported_analyzers,
                               default=argparse.SUPPRESS,
                               help="Run analysis only with the analyzers "
                                    "specified. Currently supported analyzers "
                                    "are: " +
                                    ', '.join(analyzer_types.
                                              supported_analyzers) + ".")

    analyzer_opts.add_argument('--add-compiler-defaults',
                               action='store_true',
                               default=False,
                               required=False,
                               help="Retrieve compiler-specific configuration "
                                    "from the compilers themselves, and use "
                                    "them with Clang. This is used when the "
                                    "compiler on the system is special, e.g. "
                                    "when doing cross-compilation.")

    analyzer_opts.add_argument('--saargs',
                               dest="clangsa_args_cfg_file",
                               required=False,
                               default=argparse.SUPPRESS,
                               help="File containing argument which will be "
                                    "forwarded verbatim for the Clang Static "
                                    "analyzer.")

    analyzer_opts.add_argument('--tidyargs',
                               dest="tidy_args_cfg_file",
                               required=False,
                               default=argparse.SUPPRESS,
                               help="File containing argument which will be "
                                    "forwarded verbatim for the Clang-Tidy "
                                    "analyzer.")

    checkers_opts = parser.add_argument_group(
        "checker configuration",
        "See 'codechecker-checkers' for the list of available checkers. "
        "You can fine-tune which checkers to use in the analysis by setting "
        "the enabled and disabled flags starting from the bigger groups "
        "and going inwards, e.g. '-e core -d core.uninitialized -e "
        "core.uninitialized.Assign' will enable every 'core' checker, but "
        "only 'core.uninitialized.Assign' from the 'core.uninitialized' "
        "group. Please consult the manual for details. Disabling certain "
        "checkers - such as the 'core' group - is unsupported by the LLVM/"
        "Clang community, and thus discouraged.")

    checkers_opts.add_argument('-e', '--enable',
                               dest="enable",
                               metavar='checker/checker-group',
                               default=argparse.SUPPRESS,
                               action=OrderedCheckersAction,
                               help="Set a checker (or checker group) "
                                    "to BE USED in the analysis.")

    checkers_opts.add_argument('-d', '--disable',
                               dest="disable",
                               metavar='checker/checker-group',
                               default=argparse.SUPPRESS,
                               action=OrderedCheckersAction,
                               help="Set a checker (or checker group) "
                                    "to BE PROHIBITED from use in the "
                                    "analysis.")

    # TODO: Analyze does not know '-u', only '--suppress'
    parser.add_argument('-u', '--suppress',
                        type=str,
                        dest="suppress",
                        default=argparse.SUPPRESS,
                        required=False,
                        help="Path of the suppress file to use. Records in "
                             "the suppress file are used to suppress the "
                             "storage of certain results when parsing the "
                             "analyses' report. (Reports to an analysis "
                             "result can also be suppressed in the source "
                             "code -- please consult the manual on how to do "
                             "so.) NOTE: The suppress file relies on the "
                             "\"bug identifier\" generated by the analyzers "
                             "which is experimental, take care when relying "
                             "on it.")

    dbmodes = parser.add_argument_group("database arguments")

    dbmodes = dbmodes.add_mutually_exclusive_group(required=False)

    # SQLite is the default, and for 'check', it was deprecated.
    # TODO: In 'store', --sqlite has been replaced as an option to specify the
    # .sqlite file, essentially replacing the concept of 'workspace'.
    dbmodes.add_argument('--sqlite',
                         action=DeprecatedOptionAction)

    dbmodes.add_argument('--postgresql',
                         dest="postgresql",
                         action='store_true',
                         required=False,
                         default=argparse.SUPPRESS,
                         help="Specifies that a PostgreSQL database is to be "
                              "used instead of SQLite. See the \"PostgreSQL "
                              "arguments\" section on how to configure the "
                              "database connection.")

    pgsql = parser.add_argument_group("PostgreSQL arguments",
                                      "Values of these arguments are ignored, "
                                      "unless '--postgresql' is specified!")

    # WARNING: '--dbaddress' default value influences workspace creation
    # in SQLite.
    # TODO: These are '--db-something' in 'store', not '--dbsomething'.
    pgsql.add_argument('--dbaddress',
                       type=str,
                       dest="dbaddress",
                       default="localhost",
                       required=False,
                       help="Database server address.")

    pgsql.add_argument('--dbport',
                       type=int,
                       dest="dbport",
                       default=5432,
                       required=False,
                       help="Database server port.")

    pgsql.add_argument('--dbusername',
                       type=str,
                       dest="dbusername",
                       default='codechecker',
                       required=False,
                       help="Username to use for connection.")

    pgsql.add_argument('--dbname',
                       type=str,
                       dest="dbname",
                       default="codechecker",
                       required=False,
                       help="Name of the database to use.")

    add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    Execute a wrapper over log-analyze-store, aka 'check'.
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

    workspace = os.path.abspath(args.workspace)
    report_dir = os.path.join(workspace, 'reports')
    if not os.path.isdir(report_dir):
        os.makedirs(report_dir)

    logfile = None
    try:
        # --- Step 1.: Perform logging if build command was specified.
        if 'command' in args:
            logfile = os.path.join(workspace, 'compile_cmd.json')

            # Translate the argument list between quickcheck and log.
            log_args = argparse.Namespace(
                command=args.command,
                quiet_build=args.quiet_build,
                logfile=logfile
            )

            log_module = __load_module("log")
            __update_if_key_exists(args, log_args, "verbose")

            LOG.debug("Calling LOG with args:")
            LOG.debug(log_args)
            log_module.main(log_args)
        elif 'logfile' in args:
            logfile = args.logfile

        # --- Step 2.: Perform the analysis.
        if not os.path.exists(logfile):
            raise OSError("The specified logfile '" + logfile + "' does not "
                          "exist.")

        analyze_args = argparse.Namespace(
            logfile=[logfile],
            output_path=report_dir,
            output_format='plist',
            jobs=args.jobs,
            add_compiler_defaults=args.add_compiler_defaults
        )
        # Some arguments don't have default values.
        # We can't set these keys to None because it would result in an error
        # after the call.
        args_to_update = ['skipfile',
                          'analyzers',
                          'saargs',
                          'tidyargs',
                          'ordered_checkers'  # enable and disable.
                          ]
        for key in args_to_update:
            __update_if_key_exists(args, analyze_args, key)

        analyze_module = __load_module("analyze")
        __update_if_key_exists(args, analyze_args, "verbose")

        LOG.debug("Calling ANALYZE with args:")
        LOG.debug(analyze_args)
        analyze_module.main(analyze_args)

        # --- Step 3.: Store to database.
        # TODO: The store command supposes that in case of PostgreSQL a
        # database instance is already running. The "CodeChecker check" command
        # is able to start its own instance in the given workdir, so we pass
        # this argument to the argument list. Although this is not used by
        # store command at all, the SQL utility is still able to start the
        # database. When changing this behavior, the workspace argument should
        # be removed from here.
        store_args = argparse.Namespace(
            workspace=args.workspace,
            input=[report_dir],
            input_format='plist',
            jobs=args.jobs,
            force=args.force,
            dbaddress=args.dbaddress,
            dbport=args.dbport,
            dbusername=args.dbusername,
            dbname=args.dbname
        )
        # Some arguments don't have default values.
        # We can't set these keys to None because it would result in an error
        # after the call.
        if 'postgresql' in args:
            __update_if_key_exists(args, store_args, 'postgresql')
        else:
            # If we are saving to a SQLite database, the wrapped 'check'
            # command used to do it in the workspace folder.
            setattr(store_args, 'sqlite', os.path.join(workspace,
                                                       'codechecker.sqlite'))
            setattr(store_args, 'postgresql', False)

        args_to_update = ['suppress',
                          'name'
                          ]
        for key in args_to_update:
            __update_if_key_exists(args, store_args, key)

        store_module = __load_module("store")
        __update_if_key_exists(args, store_args, "verbose")

        LOG.debug("Calling STORE with args:")
        LOG.debug(store_args)
        store_module.main(store_args)

        # Show a hint for server start.
        db_data = ""
        if 'postgresql' in args:
            db_data += " --postgresql" \
                       + " --dbname " + args.dbname \
                       + " --dbport " + str(args.dbport) \
                       + " --dbusername " + args.dbusername

        LOG.info("To view results run:\nCodeChecker server -w " +
                 args.workspace + db_data)
    except ImportError:
        LOG.error("Check failed: couldn't import a library.")
    except Exception as ex:
        LOG.error("Running check failed. " + ex.message)
    finally:
        LOG.debug("Cleaning up reports folder ...")
        shutil.rmtree(report_dir)

        if 'command' in args and logfile:
            # Only remove the build.json if it was on-the-fly created by us!
            LOG.debug("Cleaning up build.json ...")
            os.remove(logfile)

    LOG.debug("Check finished.")
