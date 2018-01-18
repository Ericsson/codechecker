# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handler for the subcommand that is used to start and manage CodeChecker
servers, which are used to query analysis report information.
"""

import argparse
import errno
import json
import os
import socket
import sys

from alembic import config
from alembic import script
from sqlalchemy.orm import sessionmaker

from shared.ttypes import DBStatus

from libcodechecker import generic_package_context
from libcodechecker import generic_package_suppress_handler
from libcodechecker import host_check
from libcodechecker import logger
from libcodechecker import output_formatters
from libcodechecker import session_manager
from libcodechecker import util
from libcodechecker.analyze import analyzer_env
from libcodechecker.server import server
from libcodechecker.server import instance_manager
from libcodechecker.server.database import database
from libcodechecker.server.database import database_status
from libcodechecker.server.database.config_db_model \
    import IDENTIFIER as CONFIG_META
from libcodechecker.server.database.config_db_model \
    import Product as ORMProduct
from libcodechecker.server.database.run_db_model \
    import IDENTIFIER as RUN_META


LOG = logger.get_logger('server')


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker server',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "The CodeChecker Web server is used to handle the "
                       "storage and navigation of analysis results. A "
                       "started server can be connected to via a Web "
                       "browser, or by using the 'CodeChecker cmd' "
                       "command-line client.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Start and manage the CodeChecker Web server."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    # TODO: --workspace is an outdated concept in 'store'. Later on,
    # it shall be deprecated, as changes to db_handler commence.
    parser.add_argument('-w', '--workspace',
                        type=str,
                        dest="workspace",
                        default=util.get_default_workspace(),
                        required=False,
                        help="Directory where CodeChecker can store analysis "
                             "result related data, such as the database. "
                             "(Cannot be specified at the same time with "
                             "'--sqlite' or '--config-directory'.)")

    parser.add_argument('-f', '--config-directory',
                        type=str,
                        dest="config_directory",
                        default=util.get_default_workspace(),
                        required=False,
                        help="Directory where CodeChecker server should read "
                             "server-specific configuration (such as "
                             "authentication settings, SSL certificate"
                             " (cert.pem) and key (key.pem)) from.")

    parser.add_argument('--host',
                        type=str,
                        dest="listen_address",
                        default="localhost",
                        required=False,
                        help="The IP address or hostname of the server on "
                             "which it should listen for connections.")

    # TODO: -v/--view-port is too verbose. The server's -p/--port is used
    # symmetrically in 'CodeChecker cmd' anyways.
    parser.add_argument('-v', '--view-port',  # TODO: <- Deprecate and remove.
                        '-p', '--port',
                        type=int,
                        dest="view_port",
                        metavar='PORT',
                        default=8001,
                        required=False,
                        help="The port which will be used as listen port for "
                             "the server.")

    # TODO: This should be removed later on, in favour of --host.
    parser.add_argument('--not-host-only',
                        dest="not_host_only",
                        action="store_true",
                        required=False,
                        help="If specified, storing and viewing the results "
                             "will be possible not only by browsers and "
                             "clients running locally, but to everyone, who "
                             "can access the server over the Internet. "
                             "(Equivalent to specifying '--host \"\"'.)")

    parser.add_argument('--skip-db-cleanup',
                        dest="skip_db_cleanup",
                        action='store_true',
                        default=False,
                        required=False,
                        help="Skip performing cleanup jobs on the database "
                             "like removing unused files.")

    dbmodes = parser.add_argument_group("configuration database arguments")

    dbmodes = dbmodes.add_mutually_exclusive_group(required=False)

    dbmodes.add_argument('--sqlite',
                         type=str,
                         dest="sqlite",
                         metavar='SQLITE_FILE',
                         default=os.path.join(
                             '<CONFIG_DIRECTORY>',
                             "config.sqlite"),
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
                       default="config",
                       required=False,
                       help="Name of the database to use.")

    root_account = parser.add_argument_group(
        "root account arguments",
        "Servers automatically create a root user to access the server's "
        "configuration via the clients. This user is created at first start "
        "and saved in the CONFIG_DIRECTORY, and the credentials are printed "
        "to the server's standard output. The plaintext credentials are "
        "NEVER accessible again.")

    root_account.add_argument('--reset-root',
                              dest="reset_root",
                              action='store_true',
                              default=argparse.SUPPRESS,
                              required=False,
                              help="Force the server to recreate the master "
                                   "superuser (root) account name and "
                                   "password. The previous credentials will "
                                   "be invalidated, and the new ones will be "
                                   "printed to the standard output.")

    root_account.add_argument('--force-authentication',
                              dest="force_auth",
                              action='store_true',
                              default=argparse.SUPPRESS,
                              required=False,
                              help="Force the server to run in "
                                   "authentication requiring mode, despite "
                                   "the configuration value in "
                                   "'server_config.json'. This is needed "
                                   "if you need to edit the product "
                                   "configuration of a server that would not "
                                   "require authentication otherwise.")

    instance_mgmnt = parser.add_argument_group("running server management")

    instance_mgmnt = instance_mgmnt. \
        add_mutually_exclusive_group(required=False)

    instance_mgmnt.add_argument('-l', '--list',
                                dest="list",
                                action='store_true',
                                default=argparse.SUPPRESS,
                                required=False,
                                help="List the servers that has been started "
                                     "by you.")

    # TODO: '-s' was removed from 'quickcheck', it shouldn't be here either?
    instance_mgmnt.add_argument('-s', '--stop',
                                dest="stop",
                                action='store_true',
                                default=argparse.SUPPRESS,
                                required=False,
                                help="Stops the server associated with "
                                     "the given view-port and workspace.")

    instance_mgmnt.add_argument('--stop-all',
                                dest="stop_all",
                                action='store_true',
                                default=argparse.SUPPRESS,
                                required=False,
                                help="Stops all of your running CodeChecker "
                                     "server instances.")

    database_mgmnt = parser.add_argument_group(
            "Database management arguments.",
            """WARNING these commands needs to be called with the same
            workspace and configuration arguments as the server so the
            configuration database will be found which is required for the
            schema migration. Migration can be done without a running server
            but pay attention to use the same arguments which will be used to
            start the server.
            NOTE:
            Before migration it is advised to create a full a backup of
            the product databases.
            """)

    database_mgmnt = database_mgmnt. \
        add_mutually_exclusive_group(required=False)

    database_mgmnt.add_argument('--db-status',
                                type=str,
                                dest="status",
                                action='store',
                                default=argparse.SUPPRESS,
                                required=False,
                                help="Name of the product to get "
                                     "the database status for. "
                                     "Use 'all' to list the database "
                                     "statuses for all of the products.")

    database_mgmnt.add_argument('--db-upgrade-schema',
                                type=str,
                                dest='product_to_upgrade',
                                action='store',
                                default=argparse.SUPPRESS,
                                required=False,
                                help="Name of the product to upgrade to the "
                                     "latest database schema available in "
                                     "the package. Use 'all' to upgrade all "
                                     "of the products."
                                     "NOTE: Before migration it is advised"
                                     " to create a full backup of "
                                     "the product databases.")

    logger.add_verbose_arguments(parser)

    def __handle(args):
        """Custom handler for 'server' so custom error messages can be
        printed without having to capture 'parser' in main."""

        def arg_match(options):
            return util.arg_match(options, sys.argv[1:])

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

        # --not-host-only is a "shortcut", actually a to-be-deprecated
        # call which means '--host ""'.
        # TODO: Actually deprecate --not-host-only later on.
        options = ['--not-host-only', '--host']
        if set(arg_match(options)) == set(options):
            parser.error("argument --not-host-only: not allowed with "
                         "argument --host, as it is a shortcut to --host "
                         "\"\"")
        else:
            # Apply the shortcut.
            if len(arg_match(['--not-host-only'])) > 0:
                args.listen_address = ""  # Listen on every interface.

            # --not-host-only is just a shortcut optstring, no actual use
            # is intended later on.
            delattr(args, 'not_host_only')

        # --workspace and --sqlite cannot be specified either, as
        # both point to a database location.
        options = ['--sqlite', '--workspace']
        options_short = ['--sqlite', '-w']
        if set(arg_match(options)) == set(options) or \
                set(arg_match(options_short)) == set(options_short):
            parser.error("argument --sqlite: not allowed with "
                         "argument --workspace")

        # --workspace and --config-directory also aren't allowed together now,
        # the latter one is expected to replace the earlier.
        options = ['--config-directory', '--workspace']
        options_short = ['--config-directory', '-w']
        if set(arg_match(options)) == set(options) or \
                set(arg_match(options_short)) == set(options_short):
            parser.error("argument --config-directory: not allowed with "
                         "argument --workspace")

        # If workspace is specified, sqlite is workspace/config.sqlite
        # and config_directory is the workspace directory.
        if len(arg_match(['--workspace', '-w'])) > 0:
            args.config_directory = args.workspace
            args.sqlite = os.path.join(args.workspace,
                                       'config.sqlite')
            setattr(args, 'dbdatadir', os.path.join(args.workspace,
                                                    'pgsql_data'))

        # Workspace should not exist as a Namespace key.
        delattr(args, 'workspace')

        if '<CONFIG_DIRECTORY>' in args.sqlite:
            # Replace the placeholder variable with the actual value.
            args.sqlite = args.sqlite.replace('<CONFIG_DIRECTORY>',
                                              args.config_directory)

        if 'postgresql' not in args:
            # Later called database modules need the argument to be actually
            # present, even though the default is suppressed in the optstring.
            setattr(args, 'postgresql', False)

            # This is not needed by the database starter as we are
            # running SQLite.
            if 'dbdatadir' in args:
                delattr(args, 'dbdatadir')
        else:
            # If --postgresql is given, --sqlite is useless.
            delattr(args, 'sqlite')

        # If everything is fine, do call the handler for the subcommand.
        main(args)

    parser.set_defaults(func=__handle)


def print_prod_status(prod_status):
    """
    Print the database statuses for each of the products.
    """

    header = ['Product endpoint', 'Database status',
              'Database location',
              'Schema version in the database',
              'Schema version in the package']
    rows = []

    for k, v in prod_status.items():
        db_status, schema_ver, package_ver, db_location = v
        db_status_msg = database_status.db_status_msg.get(db_status)
        if schema_ver == package_ver:
            schema_ver += " (up to date)"
        rows.append([k, db_status_msg, db_location, schema_ver, package_ver])

    prod_status = output_formatters.twodim_to_str('table',
                                                  header,
                                                  rows,
                                                  sort_by_column_number=0)
    print(prod_status)


def get_schema_version_from_package(migration_root):
    """
    Returns the latest schema version in the package.
    """

    cfg = config.Config()
    cfg.set_main_option("script_location", migration_root)
    pckg_schema_ver = script.ScriptDirectory.from_config(cfg)
    return pckg_schema_ver.get_current_head()


def check_product_db_status(cfg_sql_server, context):
    """
    Check the products for database statuses.

    :returns: dictionary of product endpoints with database statuses
    """

    migration_root = context.run_migration_root

    engine = cfg_sql_server.create_engine()
    config_session = sessionmaker(bind=engine)
    sess = config_session()

    try:
        products = sess.query(ORMProduct).all()
    except Exception as ex:
        LOG.debug(ex)
        LOG.error("Failed to get product configurations from the database.")
        LOG.error("Please check your command arguments.")
        sys.exit(1)

    package_schema = get_schema_version_from_package(migration_root)

    db_errors = [DBStatus.FAILED_TO_CONNECT,
                 DBStatus.MISSING,
                 DBStatus.SCHEMA_INIT_ERROR,
                 DBStatus.SCHEMA_MISSING]

    cc_env = analyzer_env.get_check_env(context.path_env_extra,
                                        context.ld_lib_path_extra)
    prod_status = {}
    for pd in products:
        db = database.SQLServer.from_connection_string(pd.connection,
                                                       RUN_META,
                                                       migration_root,
                                                       interactive=False,
                                                       env=cc_env)
        db_location = db.get_db_location()
        ret = db.connect()
        s_ver = db.get_schema_version()
        if s_ver in db_errors:
            s_ver = None
        prod_status[pd.endpoint] = (ret, s_ver, package_schema, db_location)

    sess.commit()
    sess.close()
    engine.dispose()

    return prod_status


def __db_status_check(cfg_sql_server, context, product_name=None):
    """
    Check and print database statuses for the given product.
    """
    if not product_name:
        return 0

    LOG.debug("Checking database status for " + product_name +
              " product.")

    prod_statuses = check_product_db_status(cfg_sql_server, context)

    if product_name != 'all':
        avail = prod_statuses.get(product_name)
        if not avail:
            LOG.error("No product was found with this endpoint: " +
                      str(product_name))
            return 1

        prod_statuses = {k: v for k, v in prod_statuses.items()
                         if k == product_name}

    print_prod_status(prod_statuses)
    return 0


def __db_migration(cfg_sql_server, context, product_to_upgrade='all'):
    """
    Handle database management.
    Schema checking and migration.
    """
    LOG.info("Preparing schema upgrade for " + str(product_to_upgrade))
    product_name = product_to_upgrade

    prod_statuses = check_product_db_status(cfg_sql_server, context)
    prod_to_upgrade = []

    if product_name != 'all':
        avail = prod_statuses.get(product_name)
        if not avail:
            LOG.error("No product was found with this endpoint: " +
                      product_name)
            return 1
        prod_to_upgrade.append(product_name)
    else:
        prod_to_upgrade = list(prod_statuses.keys())

    migration_root = context.run_migration_root

    LOG.warning("Please note after migration only "
                "newer CodeChecker versions can be used "
                "to start the server")
    LOG.warning("It is advised to make a full backup of your "
                "run databases.")

    cc_env = analyzer_env.get_check_env(context.path_env_extra,
                                        context.ld_lib_path_extra)
    for prod in prod_to_upgrade:
        LOG.info("========================")
        LOG.info("Checking: " + prod)
        engine = cfg_sql_server.create_engine()
        config_session = sessionmaker(bind=engine)
        sess = config_session()

        product = sess.query(ORMProduct).filter(
                ORMProduct.endpoint == prod).first()
        db = database.SQLServer.from_connection_string(product.connection,
                                                       RUN_META,
                                                       migration_root,
                                                       interactive=False,
                                                       env=cc_env)

        db_status = db.connect()

        msg = database_status.db_status_msg.get(db_status,
                                                'Unknown database status')

        LOG.info(msg)
        if db_status == DBStatus.SCHEMA_MISSING:
            question = 'Do you want to initialize a new schema for ' \
                        + product.endpoint + '? Y(es)/n(o) '
            if util.get_user_input(question):
                ret = db.connect(init=True)
                msg = database_status.db_status_msg.get(
                    ret, 'Unknown database status')
            else:
                LOG.info("No schema initialization was done.")

        elif db_status == DBStatus.SCHEMA_MISMATCH_OK:
            question = 'Do you want to upgrade to new schema for ' \
                        + product.endpoint + '? Y(es)/n(o) '
            if util.get_user_input(question):
                LOG.info("Upgrading schema ...")
                ret = db.upgrade()
                LOG.info("Done.")
                msg = database_status.db_status_msg.get(
                    ret, 'Unknown database status')
            else:
                LOG.info("No schema migration was done.")

        sess.commit()
        sess.close()
        engine.dispose()
        LOG.info("========================")
    return 0


def __instance_management(args):
    """Handles the instance-manager commands --list/--stop/--stop-all."""

    # TODO: The server stopping and listing must be revised on its invocation
    # once "workspace", as a concept, is removed.
    # QUESTION: What is the bestest way here to identify a server for the user?
    if 'list' in args:
        instances = instance_manager.get_instances()

        instances_on_multiple_hosts = any(True for inst in instances
                                          if inst['hostname'] !=
                                          socket.gethostname())
        if not instances_on_multiple_hosts:
            head = ['Workspace', 'View port']
        else:
            head = ['Workspace', 'Computer host', 'View port']

        rows = []
        for instance in instance_manager.get_instances():
            if not instances_on_multiple_hosts:
                rows.append((instance['workspace'], str(instance['port'])))
            else:
                rows.append((instance['workspace'],
                             instance['hostname']
                             if instance['hostname'] != socket.gethostname()
                             else '',
                             str(instance['port'])))

        print("Your running CodeChecker servers:")
        print(output_formatters.twodim_to_str('table', head, rows))
    elif 'stop' in args or 'stop_all' in args:
        for i in instance_manager.get_instances():
            if i['hostname'] != socket.gethostname():
                continue

            # A STOP only stops the server associated with the given workspace
            # and view-port.
            if 'stop' in args and \
                not (i['port'] == args.view_port and
                     os.path.abspath(i['workspace']) ==
                     os.path.abspath(args.config_directory)):
                continue

            try:
                util.kill_process_tree(i['pid'])
                LOG.info("Stopped CodeChecker server running on port {0} "
                         "in workspace {1} (PID: {2})".
                         format(i['port'], i['workspace'], i['pid']))
            except Exception:
                # Let the exception come out if the commands fail
                LOG.error("Couldn't stop process PID #" + str(i['pid']))
                raise


def server_init_start(args):
    """
    Start or manage a CodeChecker report server.
    """

    if 'list' in args or 'stop' in args or 'stop_all' in args:
        __instance_management(args)
        sys.exit(0)

    # Actual server starting from this point.
    if not host_check.check_zlib():
        raise Exception("zlib is not available on the system!")

    # WARNING
    # In case of SQLite args.dbaddress default value is used
    # for which the is_localhost should return true.
    if util.is_localhost(args.dbaddress) and \
            not os.path.exists(args.config_directory):
        os.makedirs(args.config_directory)

    # Make sure the SQLite file can be created if it not exists.
    if 'sqlite' in args and \
            not os.path.isdir(os.path.dirname(args.sqlite)):
        os.makedirs(os.path.dirname(args.sqlite))

    if 'reset_root' in args:
        try:
            os.remove(os.path.join(args.config_directory, 'root.user'))
            LOG.info("Master superuser (root) credentials invalidated and "
                     "deleted. New ones will be generated...")
        except OSError:
            # File doesn't exist.
            pass

    if 'force_auth' in args:
        LOG.info("'--force-authentication' was passed as a command-line "
                 "option. The server will ask for users to authenticate!")

    context = generic_package_context.get_context()
    context.codechecker_workspace = args.config_directory
    session_manager.SessionManager.CodeChecker_Workspace = \
        args.config_directory
    context.db_username = args.dbusername

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    cfg_sql_server = database.SQLServer.from_cmdline_args(
        vars(args), CONFIG_META, context.config_migration_root,
        interactive=True, env=check_env)

    LOG.info("Checking configuration database ...")
    db_status = cfg_sql_server.connect()
    db_status_msg = database_status.db_status_msg.get(db_status)
    LOG.info(db_status_msg)

    if db_status == DBStatus.SCHEMA_MISSING:
        LOG.debug("Config database schema is missing, initializing new.")
        db_status = cfg_sql_server.connect(init=True)
        if db_status != DBStatus.OK:
            LOG.error("Config database initialization failed!")
            LOG.error("Please check debug logs.")
            sys.exit(1)

    if db_status == DBStatus.SCHEMA_MISMATCH_NO:
        LOG.debug("Configuration database schema mismatch.")
        LOG.debug("No schema upgrade is possible.")
        sys.exit(1)

    if db_status == DBStatus.SCHEMA_MISMATCH_OK:
        LOG.debug("Configuration database schema mismatch.")
        LOG.debug("Schema upgrade is possible.")
        LOG.warning("Please note after migration only "
                    "newer CodeChecker versions can be used"
                    "to start the server")
        LOG.warning("It is advised to make a full backup of your "
                    "configuration database")

        LOG.warning(cfg_sql_server.get_db_location())

        question = 'Do you want to upgrade to the new schema?' \
                   ' Y(es)/n(o) '
        if util.get_user_input(question):
            print("Upgrading schema ...")
            ret = cfg_sql_server.upgrade()
            msg = database_status.db_status_msg.get(
                ret, 'Unknown database status')
            print(msg)
            if ret != DBStatus.OK:
                LOG.error("Schema migration failed")
                syst.exit(ret)
        else:
            LOG.info("No schema migration was done.")
            sys.exit(0)

    if db_status == DBStatus.MISSING:
        LOG.error("Missing configuration database.")
        LOG.error("Server can not be started.")
        sys.exit(1)

    # Configuration database setup and check is needed before database
    # statuses can be checked.
    try:
        if args.status:
            ret = __db_status_check(cfg_sql_server, context, args.status)
            sys.exit(ret)
    except AttributeError:
        LOG.debug('Status was not in the arguments.')

    try:
        if args.product_to_upgrade:
            ret = __db_migration(cfg_sql_server, context,
                                 args.product_to_upgrade)
            sys.exit(ret)
    except AttributeError:
        LOG.debug('Product upgrade was not in the arguments.')

    # Create the main database link from the arguments passed over the
    # command line.
    default_product_path = os.path.join(args.config_directory,
                                        'Default.sqlite')
    create_default_product = 'sqlite' in args and \
                             not os.path.exists(default_product_path)

    if create_default_product:
        # Create a default product and add it to the configuration database.

        LOG.debug("Create default product...")
        LOG.debug("Configuring schema and migration...")

        prod_server = database.SQLiteDatabase(
            default_product_path, RUN_META,
            context.run_migration_root, check_env)

        LOG.debug("Checking 'Default' product database.")
        db_status = prod_server.connect()
        if db_status != DBStatus.MISSING:
            db_status = prod_server.connect(init=True)
            LOG.error(database_status.db_status_msg.get(db_status))
            if db_status != DBStatus.OK:
                LOG.error("Failed to configure default product")
                sys.exit(1)

        product_conn_string = prod_server.get_connection_string()

        server.add_initial_run_database(
            cfg_sql_server, product_conn_string)

        LOG.info("Product 'Default' at '{0}' created and set up."
                 .format(default_product_path))

    prod_statuses = check_product_db_status(cfg_sql_server, context)

    upgrade_available = {}
    for k, v in prod_statuses.items():
        db_status, _, _, _ = v
        if db_status == DBStatus.SCHEMA_MISMATCH_OK or \
                db_status == DBStatus.SCHEMA_MISSING:
            upgrade_available[k] = v

    if upgrade_available:
        print_prod_status(prod_statuses)
        LOG.warning("Multiple products can be upgraded, make a backup!")
        __db_migration(cfg_sql_server, context)

    prod_statuses = check_product_db_status(cfg_sql_server, context)
    print_prod_status(prod_statuses)

    non_ok_db = False
    for k, v in prod_statuses.items():
        db_status, _, _, _ = v
        if db_status != DBStatus.OK:
            non_ok_db = True
        break

    if non_ok_db:
        msg = "There are some database issues. " \
              "Do you want to start the " \
              "server? Y(es)/n(o) "
        if not util.get_user_input(msg):
            sys.exit(1)

    # Start database viewer.
    checker_md_docs = os.path.join(context.doc_root, 'checker_md_docs')
    checker_md_docs_map = os.path.join(checker_md_docs,
                                       'checker_doc_map.json')
    with open(checker_md_docs_map, 'r') as dFile:
        checker_md_docs_map = json.load(dFile)

    package_data = {'www_root': context.www_root,
                    'doc_root': context.doc_root,
                    'checker_md_docs': checker_md_docs,
                    'checker_md_docs_map': checker_md_docs_map,
                    'version': context.package_git_tag}

    suppress_handler = generic_package_suppress_handler. \
        GenericSuppressHandler(None, False)

    try:
        server.start_server(args.config_directory,
                            package_data,
                            args.view_port,
                            cfg_sql_server,
                            suppress_handler,
                            args.listen_address,
                            'force_auth' in args,
                            args.skip_db_cleanup,
                            context,
                            check_env)
    except socket.error as err:
        if err.errno == errno.EADDRINUSE:
            LOG.error("Server can't be started, maybe the given port number "
                      "({}) is already used. Check the connection "
                      "parameters.".format(args.view_port))
            sys.exit(1)
        else:
            raise


def main(args):
    """
    Setup a logger server based on the configuration and
    manage the Codechecker server.
    """
    with logger.LOG_CFG_SERVER(args.verbose):
        server_init_start(args)
