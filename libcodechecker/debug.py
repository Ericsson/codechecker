# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Create GNU GDB debug files for failed analysis commands of the most recent
run in a given database.
"""

import argparse
import itertools
import os
import sys

import sqlalchemy
from sqlalchemy.sql import and_

from libcodechecker import database_handler
from libcodechecker import generic_package_context
from libcodechecker import util
# TODO: Refers subpackage library
from libcodechecker.analyze import analyzer_crash_handler
from libcodechecker.analyze import analyzer_env
from libcodechecker.database_handler import SQLServer
from libcodechecker.logger import add_verbose_arguments
from libcodechecker.logger import LoggerFactory
from libcodechecker.orm_model import BuildAction
from libcodechecker.orm_model import Run

LOG = LoggerFactory.get_new_logger('GDB DEBUG CREATOR')


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker debug',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Create debug logs and GNU GDB debug dump files for "
                       "all compilation commands whose analysis failed in the "
                       "most recent analysis run in the database specified.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Create debug log files and GDB dumps for the failed commands "
                "in the most recent run."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    # TODO: --workspace is an outdated concept in 'store' and 'server'. Later
    # on, it shall be deprecated, as changes to db_handler commence.
    parser.add_argument('-w', '--workspace',
                        type=str,
                        dest="workspace",
                        default=util.get_default_workspace(),
                        required=False,
                        help="Directory where CodeChecker can find analysis "
                             "result related data, such as the database. "
                             "(Cannot be specified at the same time with "
                             "'--sqlite' and '--output'.)")

    parser.add_argument('-o', '--output',
                        type=str,
                        dest="output_dir",
                        default=os.path.join(util.get_default_workspace(),
                                             'dumps'),
                        required=False,
                        help="Directory where the created files should be "
                             "put to.")

    parser.add_argument('-f', '--force',
                        dest="force",
                        default=False,
                        action='store_true',
                        required=False,
                        help="Overwrite already existing debug files.")

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
    # TODO: --dbSOMETHING arguments are kept to not break interface from
    # old command. Database using commands such as "CodeChecker store" no
    # longer supports these --- it would be ideal to break and remove args
    # with this style and only keep --db-SOMETHING.
    pgsql.add_argument('--dbaddress', '--db-host',
                       type=str,
                       dest="dbaddress",
                       default="localhost",
                       required=False,
                       help="Database server address.")

    pgsql.add_argument('--dbport', '--db-port',
                       type=int,
                       dest="dbport",
                       default=5432,
                       required=False,
                       help="Database server port.")

    pgsql.add_argument('--dbusername', '--db-username',
                       type=str,
                       dest="dbusername",
                       default='codechecker',
                       required=False,
                       help="Username to use for connection.")

    pgsql.add_argument('--dbname', '--db-name',
                       type=str,
                       dest="dbname",
                       default="codechecker",
                       required=False,
                       help="Name of the database to use.")

    add_verbose_arguments(parser)

    def __handle(args):
        """Custom handler for 'server' so custom error messages can be
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
        options = ['--dbaddress', '--dbport', '--dbusername', '--dbname',
                   '--db-host', '--db-port', '--db-username', '--db-name']
        psql_args_matching = arg_match(options)
        if any(psql_args_matching) and\
                'postgresql' not in args:
            first_matching_arg = next(iter([match for match
                                            in psql_args_matching]))
            parser.error("argument {0}: not allowed without "
                         "argument --postgresql".format(first_matching_arg))
            # parser.error() terminates with return code 2.

        # --workspace and --sqlite cannot be specified either, as
        # both point to a database location.
        options = ['--sqlite', '--workspace']
        options_short = ['--sqlite', '-w']
        if set(arg_match(options)) == set(options) or \
                set(arg_match(options_short)) == set(options_short):
            parser.error("argument --sqlite: not allowed with "
                         "argument --workspace")

        # --workspace and --output also aren't allowed together now,
        # the latter one is expected to replace the earlier.
        options = [['--output', '-o'], ['--workspace', '-w']]
        for combination in itertools.product(*options):
            # Calculate the cross-join nested loop of all the colliding args.
            if set(arg_match(combination)) == set(combination):
                parser.error("argument --output: not allowed with "
                             "argument --workspace")

        # If workspace is specified, sqlite is workspace/codechecker.sqlite
        # and config_directory is the workspace directory.
        if len(arg_match(['--workspace', '-w'])) > 0:
            args.output_dir = os.path.join(args.workspace, 'dumps')
            args.sqlite = os.path.join(args.workspace,
                                       'codechecker.sqlite')

        # Workspace should not exist as a Namespace key.
        delattr(args, 'workspace')

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


def main(args):
    """
    Create GNU GDB debug files for failed analysis commands of the most recent
    run in a given database.
    """

    context = generic_package_context.get_context()

    context.db_username = args.dbusername

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    sql_server = SQLServer.from_cmdline_args(args,
                                             context.migration_root,
                                             check_env)

    sql_server.start(context.db_version_info, wait_for_start=True, init=False)

    try:
        engine = database_handler.SQLServer.create_engine(
            sql_server.get_connection_string())
        session = sqlalchemy.orm.scoped_session(
            sqlalchemy.orm.sessionmaker(bind=engine))

        # Get latest run id.
        last_run = session.query(Run).order_by(Run.id.desc()).first()

        # Get all failed actions.
        actions = session.query(BuildAction).filter(and_(
            BuildAction.run_id == last_run.id,
            sqlalchemy.sql.func.length(BuildAction.failure_txt) != 0))

        crash_handler = analyzer_crash_handler.AnalyzerCrashHandler(context,
                                                                    check_env)

        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)

        LOG.info("Generating gdb dump files to '" + args.output_dir + "'")

        for action in actions:
            LOG.info("Processing action '" + str(action.id) + "'")
            debug_log_file = \
                os.path.join(args.output_dir,
                             "action_{0}_{1}_dump.log".format(last_run.id,
                                                              action.id))

            if not args.force and os.path.exists(debug_log_file):
                LOG.info("Skipping as debug file already exists")
                continue

            LOG.debug("Generating stack trace with gdb...")

            gdb_result = \
                crash_handler.get_crash_info(str(action.check_cmd).split())

            LOG.debug("Writing debug info to file.")

            with open(debug_log_file, 'w') as log_file:
                log_file.write('========================\n')
                log_file.write('Build command hash: \n')
                log_file.write('========================\n')
                log_file.write(action.build_cmd_hash + '\n')
                log_file.write('===============\n')
                log_file.write('Check command: \n')
                log_file.write('===============\n')
                log_file.write(action.check_cmd + '\n')
                log_file.write('==============\n')
                log_file.write('Failure text: \n')
                log_file.write('==============\n')
                log_file.write(action.failure_txt + '\n')
                log_file.write('==========\n')
                log_file.write('GDB info: \n')
                log_file.write('==========\n')
                log_file.write(gdb_result)

        LOG.info("All new debug files are placed in '" + args.output_dir + "'")

    except KeyboardInterrupt as kb_exc:
        LOG.error(str(kb_exc))
        sys.exit(1)
