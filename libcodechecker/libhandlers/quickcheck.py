# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Quickcheck implements a wrapper over 'log' + 'analyze' + 'parse', essentially
giving an easy way to perform analysis from a log command and print results to
stdout.
"""

import argparse
import os
import shutil
import tempfile

from libcodechecker import libhandlers
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.logger import add_verbose_arguments
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('QUICKCHECK')


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
        'prog': 'CodeChecker quickcheck',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Run analysis for a project with printing results "
                       "immediately on the standard output. Quickcheck only "
                       "needs a build command or an already existing logfile "
                       "and performs every step of doing the analysis in "
                       "batch.",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': "If you wish to reuse the logfile resulting from executing "
                  "the build, see 'codechecker-log'. To keep analysis "
                  "results for later, see and use 'codechecker-analyze'. "
                  "To print human-readable output from previously saved "
                  "analysis results, see 'codechecker-parse'. 'CodeChecker "
                  "quickcheck' exposes a wrapper calling these three commands "
                  "in succession. Please make sure your build command "
                  "actually builds the files -- it is advised to execute "
                  "builds on empty trees, aka. after a 'make clean', as "
                  "CodeChecker only analyzes files that had been used by the "
                  "build system.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Perform analysis on a project and print results to standard "
                "output."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    log_args = parser.add_argument_group(
        "log arguments",
        "Specify how the build information database should be obtained. You "
        "need to specify either an already existing log file, or a build "
        "command which will be used to generate a log file on the fly.")

    log_args.add_argument('-q', '--quiet-build',
                          dest="quiet_build",
                          action='store_true',
                          required=False,
                          default=argparse.SUPPRESS,
                          help="Do not print the output of the build tool "
                               "into the output of this command.")

    log_args = log_args.add_mutually_exclusive_group(required=True)

    log_args.add_argument('-b', '--build',
                          type=str,
                          dest="command",
                          default=argparse.SUPPRESS,
                          help="Execute and record a build command. Build "
                               "commands can be simple calls to 'g++' or "
                               "'clang++' or 'make', but a more complex "
                               "command, or the call of a custom script file "
                               "is also supported.")

    log_args.add_argument('-l', '--logfile',
                          type=str,
                          dest="logfile",
                          default=argparse.SUPPRESS,
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

    analyzer_opts.add_argument('-i', '--ignore', '--skip',
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
                               required=False,
                               default=argparse.SUPPRESS,
                               help="Retrieve compiler-specific configuration "
                                    "from the analyzers themselves, and use "
                                    "them with Clang. This is used when the "
                                    "compiler on the system is special, e.g. "
                                    "when doing cross-compilation.")

    # TODO: One day, get rid of these. See Issue #36, #427.
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

    output_opts = parser.add_argument_group("output arguments")

    output_opts.add_argument('--print-steps',
                             dest="print_steps",
                             action="store_true",
                             required=False,
                             default=argparse.SUPPRESS,
                             help="Print the steps the analyzers took in "
                                  "finding the reported defect.")

    add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    Execute a wrapper over log-analyze-parse, aka 'quickcheck'.
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

    workspace = tempfile.mkdtemp(prefix='codechecker-qc')
    logfile = None
    try:
        # --- Step 1.: Perform logging if build command was specified.
        if 'command' in args:
            logfile = os.path.join(workspace, 'compile_cmd.json')

            # Translate the argument list between quickcheck and log.
            log_args = argparse.Namespace(
                command=args.command,
                logfile=logfile
            )
            __update_if_key_exists(args, log_args, "quiet_build")
            __update_if_key_exists(args, log_args, "verbose")

            log_module = __load_module("log")
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
            output_path=workspace,
            output_format='plist',
            clean=True,
            jobs=args.jobs
        )
        # Some arguments don't have default values.
        # We can't set these keys to None because it would result in an error
        # after the call.
        args_to_update = ['skipfile',
                          'analyzers',
                          'add_compiler_defaults',
                          'clangsa_args_cfg_file',
                          'tidy_args_cfg_file',
                          'ordered_checkers'  # enable and disable.
                          ]
        for key in args_to_update:
            __update_if_key_exists(args, analyze_args, key)
        __update_if_key_exists(args, analyze_args, "verbose")

        analyze_module = __load_module("analyze")
        LOG.debug("Calling ANALYZE with args:")
        LOG.debug(analyze_args)

        analyze_module.main(analyze_args)

        # --- Step 3.: Print to stdout.
        parse_args = argparse.Namespace(
            input=[workspace],
            input_format='plist'
        )
        __update_if_key_exists(args, parse_args, "print_steps")
        __update_if_key_exists(args, parse_args, "verbose")

        parse_module = __load_module("parse")
        LOG.debug("Calling PARSE with args:")
        LOG.debug(parse_args)

        parse_module.main(parse_args)
    except ImportError:
        LOG.error("Quickcheck failed: couldn't import a library.")
    except Exception as ex:
        LOG.error("Running quickcheck failed. " + ex.message)
    finally:
        shutil.rmtree(workspace)

    LOG.debug("Quickcheck finished.")
