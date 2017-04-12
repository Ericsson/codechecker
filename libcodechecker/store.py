# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
'CodeChecker store' parses a list of analysis results and stores them in the
database.
"""

import argparse
import datetime
import getpass
import json
import multiprocessing
import sys
import os

from libcodechecker import client
from libcodechecker import generic_package_context
from libcodechecker import util
from libcodechecker.analyze import analyzer_env
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.database_handler import SQLServer
from libcodechecker.log import build_action
from libcodechecker.logger import add_verbose_arguments
from libcodechecker.logger import LoggerFactory


LOG = LoggerFactory.get_new_logger('STORE')


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker store',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Store the results from one or more 'codechecker-"
                       "analyze' result files in a database.",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': "To start a server which connects to a database where "
                  "results are stored, use 'CodeChecker server'. The results "
                  "can be viewed by connecting to such a server in a Web "
                  "browser or via 'CodeChecker cmd'.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Save analysis results to a database."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('input',
                        type=str,
                        nargs='*',
                        metavar='file/folder',
                        default=os.path.join(util.get_default_workspace(),
                                             'reports'),
                        help="The analysis result files and/or folders "
                             "containing analysis results which should be "
                             "parsed and printed.")

    parser.add_argument('-t', '--type', '--input-format',
                        dest="input_format",
                        required=False,
                        choices=['plist'],
                        default='plist',
                        help="Specify the format the analysis results were "
                             "created as.")

    parser.add_argument('-j', '--jobs',
                        type=int,
                        dest="jobs",
                        required=False,
                        default=1,
                        help="Number of threads to use in storing results. "
                             "More threads mean faster operation at the cost "
                             "of using more memory.")

    parser.add_argument('-n', '--name',
                        type=str,
                        dest="name",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="The name of the analysis run to use in storing "
                             "the reports to the database. If not specified, "
                             "the '--name' parameter given to 'codechecker-"
                             "analyze' will be used, if exists.")

    # Upcoming feature planned for v6.0. Argument name and help RESERVED.
    # parser.add_argument('--group', '--group-name',
    #                    type=str,
    #                    dest="group_name",
    #                    required=False,
    #                    default=argparse.SUPPRESS,
    #                    help="Specify the \"analysis group\" the results "
    #                         "stored will belong to. An analysis group "
    #                         "consists of multiple analyses whose reports "
    #                         "are showed together in a common view -- e.g. "
    #                         "a project's view for every subproject analysed "
    #                         "separately, or all analyses of a user or a "
    #                         "team.")

    parser.add_argument('--suppress',
                        type=str,
                        dest="suppress",
                        default=argparse.SUPPRESS,
                        required=False,
                        help="Path of the suppress file to use. Records in "
                             "the suppress file are used to mark certain "
                             "stored analysis results as 'suppressed'. "
                             "(Reports to an analysis result can also be "
                             "suppressed in the source code -- please "
                             "consult the manual on how to do so.) NOTE: The "
                             "suppress file relies on the \"bug identifier\" "
                             "generated by the analyzers which is "
                             "experimental, take care when relying on it.")

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

    dbmodes = parser.add_argument_group("database arguments")

    dbmodes = dbmodes.add_mutually_exclusive_group(required=False)

    dbmodes.add_argument('--sqlite',
                         type=str,
                         dest="sqlite",
                         metavar='SQLITE_FILE',
                         default=os.path.join(
                             util.get_default_workspace(),
                             "codechecker.sqlite"),
                         required=False,
                         help="Path of the SQLite database file to use.")

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
    pgsql.add_argument('--db-host',
                       type=str,
                       dest="dbaddress",
                       default="localhost",
                       required=False,
                       help="Database server address.")

    pgsql.add_argument('--db-port',
                       type=int,
                       dest="dbport",
                       default=5432,
                       required=False,
                       help="Database server port.")

    pgsql.add_argument('--db-username',
                       type=str,
                       dest="dbusername",
                       default='codechecker',
                       required=False,
                       help="Username to use for connection.")

    pgsql.add_argument('--db-name',
                       type=str,
                       dest="dbname",
                       default="codechecker",
                       required=False,
                       help="Name of the database to use.")

    add_verbose_arguments(parser)

    def __handle(args):
        """Custom handler for 'store' so custom error messages can be
        printed without having to capture 'parser' in main."""

        def arg_match(options):
            """Checks and selects the option string specified in 'options'
            that are present in the invocation argv."""
            matched_args = []
            for option in options:
                if any([arg if option.startswith(arg) else None
                        for arg in sys.argv[1:]]):
                    matched_args.append(option)
                    continue

            return matched_args

        # See if there is a "PostgreSQL argument" specified in the invocation
        # without '--postgresql' being there. There is no way to distinguish
        # a default argument and a deliberately specified argument without
        # inspecting sys.argv.
        options = ['--db-host', '--db-port', '--db-username', '--db-name']
        psql_args_matching = arg_match(options)
        if any(psql_args_matching) and \
                'postgresql' not in args:
            first_matching_arg = next(iter([match for match
                                            in psql_args_matching]))
            parser.error("argument {0}: not allowed without "
                         "argument --postgresql".format(first_matching_arg))
            # parser.error() terminates with return code 2.

        if 'postgresql' not in args:
            # Later called database modules need the argument to be actually
            # present, even though the default is suppressed in the optstring.
            setattr(args, 'postgresql', False)
        else:
            # If --postgresql is given, --sqlite is useless.
            delattr(args, 'sqlite')

        # If everything is fine, do call the handler for the subcommand.
        main(args)

    parser.set_defaults(func=__handle)


def consume_plist(item):
    f, context = item

    LOG.debug("Parsing input file '" + f + "'")

    buildaction = build_action.BuildAction()
    if os.path.basename(f).startswith("clangsa_"):
        buildaction.analyzer_type = analyzer_types.CLANG_SA
    elif os.path.basename(f).startswith("clang-tidy_"):
        buildaction.analyzer_type = analyzer_types.CLANG_TIDY

    buildaction.original_command = "IMPORTED"

    rh = analyzer_types.construct_store_handler(buildaction,
                                                context.run_id,
                                                context.severity_map)

    rh.analyzer_returncode = 0
    rh.analyzer_cmd = ''

    # TODO: How to get file from plists?! :'(
    rh.analyzed_source_file = ''  # TODO: fill from plist.
    rh.result_file = f

    rh.handle_results()


def __get_run_name(input_list):
    """Create a runname for the stored analysis from the input list."""

    # Try to create a name from the metada JSON(s).
    names = []
    for input_path in input_list:
        metafile = os.path.join(input_path, "metadata.json")
        if os.path.isdir(input_path) and os.path.exists(metafile):
            with open(metafile, 'r') as metadata:
                metajson = json.load(metadata)

            if 'name' in metajson:
                names.append(metajson['name'])
            else:
                names.append("unnamed result folder")

    if len(names) == 1 and names[0] != "unnamed result folder":
        return names[0]
    elif len(names) > 1:
        return "multiple projects: " + ', '.join(names)
    else:
        return False


def main(args):
    """
    Store the defect results in the specified input list as bug reports in the
    database.
    """

    # To ensure the help message prints the default folder properly,
    # the 'default' for 'args.input' is a string, not a list.
    # But we need lists for the foreach here to work.
    if isinstance(args.input, str):
        args.input = [args.input]

    if 'name' not in args:
        LOG.debug("Generating name for analysis...")
        generated = __get_run_name(args.input)
        if generated:
            setattr(args, 'name', generated)
        else:
            LOG.error("No suitable name was found in the inputs for the "
                      "analysis run. Please specify one by passing argument "
                      "--name run_name in the invocation.")
            sys.exit(2)  # argparse returns error code 2 for bad invocations.

    LOG.info("Storing analysis results '" + args.name + "'")

    if args.force:
        LOG.info("argument --force was specified: the run with name '" +
                 args.name + "' will be deleted.")

    context = generic_package_context.get_context()
    context.db_username = args.dbusername

    check_commands = []
    check_durations = []
    items = []
    for input_path in args.input:
        LOG.debug("Parsing input argument: '" + input_path + "'")

        if os.path.isfile(input_path):
            if not input_path.endswith(".plist"):
                continue

            items.append((input_path, context))
        elif os.path.isdir(input_path):
            metadata_file = os.path.join(input_path, "metadata.json")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as metadata:
                    metadata_dict = json.load(metadata)
                    LOG.debug(metadata_dict)

                    if 'command' in metadata_dict:
                        check_commands.append(metadata_dict['command'])
                    if 'timestamps' in metadata_dict:
                        check_durations.append(
                            float(metadata_dict['timestamps']['end'] -
                                  metadata_dict['timestamps']['begin']))

            _, _, files = next(os.walk(input_path), ([], [], []))
            for f in files:
                if not f.endswith(".plist"):
                    continue

                items.append((os.path.join(input_path, f),
                              context))

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    sql_server = SQLServer.from_cmdline_args(args,
                                             context.migration_root,
                                             check_env)

    conn_mgr = client.ConnectionManager(sql_server,
                                        'localhost',
                                        util.get_free_port())

    sql_server.start(context.db_version_info, wait_for_start=True,
                     init=True)

    conn_mgr.start_report_server()

    with client.get_connection() as connection:
        if len(check_commands) == 0:
            command = ' '.join(sys.argv)
        elif len(check_commands) == 1:
            command = ' '.join(check_commands[0])
        else:
            command = "multiple analyze calls: " +\
                      '; '.join([' '.join(com) for com in check_commands])

        context.run_id = connection.add_checker_run(command,
                                                    args.name,
                                                    context.version,
                                                    args.force)

        if 'suppress' in args:
            if not os.path.isfile(args.suppress):
                LOG.warning("Suppress file '" + args.suppress + "' given, but "
                            "it does not exist -- will not suppress anything.")
            else:
                client.send_suppress(context.run_id, connection,
                                     os.path.realpath(args.suppress))

    pool = multiprocessing.Pool(args.jobs)

    try:
        pool.map_async(consume_plist, items, 1).get(float('inf'))
        pool.close()
    except Exception:
        pool.terminate()
        LOG.error("Storing the results failed.")
        raise  # CodeChecker.py is the invoker, it will handle this.
    finally:
        pool.join()

        with client.get_connection() as connection:
            connection.finish_checker_run(context.run_id)

            if len(check_durations) > 0:
                connection.set_run_duration(context.run_id,
                                            # Round the duration to seconds.
                                            int(sum(check_durations)))
