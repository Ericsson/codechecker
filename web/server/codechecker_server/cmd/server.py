# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handler for the subcommand that is used to start and manage CodeChecker
servers, which are used to query analysis report information.
"""


import argparse
import errno
import os
import signal
import socket
import sys
import time

import psutil
from alembic import config
from alembic import script
from sqlalchemy.orm import sessionmaker

from codechecker_api_shared.ttypes import DBStatus

from codechecker_report_converter import twodim

from codechecker_common import arg, logger, util, cmd_config

from codechecker_server import instance_manager, server
from codechecker_server.database import database
from codechecker_server.database.config_db_model \
    import IDENTIFIER as CONFIG_META
from codechecker_server.database.config_db_model \
    import Product as ORMProduct
from codechecker_server.database.run_db_model \
    import IDENTIFIER as RUN_META

from codechecker_web.shared import webserver_context, database_status, \
    host_check, env

LOG = logger.get_logger('server')


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker server',
        'formatter_class': arg.RawDescriptionDefaultHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': """
The CodeChecker Web server is used to handle the storage and navigation of
analysis results. A started server can be connected to via a Web browser, or
by using the 'CodeChecker cmd' command-line client.""",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Start and manage the CodeChecker Web server."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    default_workspace = env.get_default_workspace()

    # TODO: --workspace is an outdated concept in 'store'. Later on,
    # it shall be deprecated, as changes to db_handler commence.
    parser.add_argument('-w', '--workspace',
                        type=str,
                        dest="workspace",
                        default=default_workspace,
                        required=False,
                        help="Directory where CodeChecker can store analysis "
                             "result related data, such as the database. "
                             "(Cannot be specified at the same time with "
                             "'--sqlite' or '--config-directory'.)")

    parser.add_argument('-f', '--config-directory',
                        type=str,
                        dest="config_directory",
                        default=default_workspace,
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
                             "which it should listen for connections. "
                             "For IPv6 listening, specify an IPv6 address, "
                             "such as \"::1\".")

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
                             "(Equivalent to specifying '--host \"::\"'.)")

    parser.add_argument('--skip-db-cleanup',
                        dest="skip_db_cleanup",
                        action='store_true',
                        default=False,
                        required=False,
                        help="Skip performing cleanup jobs on the database "
                             "like removing unused files.")

    cmd_config.add_option(parser)

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
        """
Servers automatically create a root user to access the server's configuration
via the clients. This user is created at first start and saved in the
CONFIG_DIRECTORY, and the credentials are printed to the server's standard
output. The plaintext credentials are NEVER accessible again.""")

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

    instance_mgmnt.add_argument('-r', '--reload',
                                dest="reload",
                                action='store_true',
                                default=argparse.SUPPRESS,
                                required=False,
                                help="Sends the CodeChecker server process a "
                                     "SIGHUP signal, causing it to reread "
                                     "it's configuration files.")

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
            """
WARNING these commands needs to be called with the same workspace and
configuration arguments as the server so the configuration database will be
found which is required for the schema migration. Migration can be done
without a running server but pay attention to use the same arguments which
will be used to start the server.

NOTE:
Before migration it is advised to create a full a backup of the product
databases.
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
                                     "of the products. "
                                     "NOTE: Before migration it is advised"
                                     " to create a full backup of "
                                     "the product databases.")

    database_mgmnt.add_argument('--db-force-upgrade',
                                dest='force_upgrade',
                                action='store_true',
                                default=argparse.SUPPRESS,
                                required=False,
                                help="Force the server to do database "
                                     "migration without user interaction. "
                                     "NOTE: Please use with caution and "
                                     "before automatic migration it is "
                                     "advised to create a full backup of the "
                                     "product databases.")

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
                         "\"::\"")
        else:
            # Apply the shortcut.
            if arg_match(['--not-host-only']):
                args.listen_address = "::"  # Listen on every interface.

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
        if arg_match(['--workspace', '-w']):
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

        # Convert relative sqlite file path to absolute.
        if 'sqlite' in args:
            args.sqlite = os.path.abspath(args.sqlite)

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

    parser.set_defaults(
        func=__handle, func_process_config_file=cmd_config.process_config_file)


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
        rows.append([k, db_status_msg, db_location, str(schema_ver),
                     package_ver])

    prod_status = twodim.to_str('table',
                                header,
                                rows,
                                sort_by_column_number=0)
    LOG.info('Status of products:\n%s', prod_status)


def get_schema_version_from_package(migration_root):
    """
    Returns the latest schema version in the package.
    """

    cfg = config.Config()
    cfg.set_main_option("script_location", migration_root)
    pckg_schema_ver = script.ScriptDirectory.from_config(cfg)
    return pckg_schema_ver.get_current_head()


def check_product_db_status(cfg_sql_server, migration_root, environ):
    """
    Check the products for database statuses.

    :returns: dictionary of product endpoints with database statuses
    """

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

    prod_status = {}
    for pd in products:
        db = database.SQLServer.from_connection_string(pd.connection,
                                                       RUN_META,
                                                       migration_root,
                                                       interactive=False,
                                                       env=environ)
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


def __db_status_check(cfg_sql_server, migration_root, environ,
                      product_name=None):
    """
    Check and print database statuses for the given product.
    """
    if not product_name:
        return 0

    LOG.debug("Checking database status for %s product.", product_name)

    prod_statuses = check_product_db_status(cfg_sql_server, migration_root,
                                            environ)

    if product_name != 'all':
        avail = prod_statuses.get(product_name)
        if not avail:
            LOG.error("No product was found with this endpoint: %s",
                      str(product_name))
            return 1

        prod_statuses = {k: v for k, v in prod_statuses.items()
                         if k == product_name}

    print_prod_status(prod_statuses)
    return 0


def __db_migration(cfg_sql_server, migration_root, environ,
                   product_to_upgrade='all', force_upgrade=False):
    """
    Handle database management.
    Schema checking and migration.
    """
    LOG.info("Preparing schema upgrade for %s", str(product_to_upgrade))
    product_name = product_to_upgrade

    prod_statuses = check_product_db_status(cfg_sql_server,
                                            migration_root,
                                            environ)
    prod_to_upgrade = []

    if product_name != 'all':
        avail = prod_statuses.get(product_name)
        if not avail:
            LOG.error("No product was found with this endpoint: %s",
                      product_name)
            return 1
        prod_to_upgrade.append(product_name)
    else:
        prod_to_upgrade = list(prod_statuses.keys())

    LOG.warning("Please note after migration only "
                "newer CodeChecker versions can be used "
                "to start the server")
    LOG.warning("It is advised to make a full backup of your "
                "run databases.")

    for prod in prod_to_upgrade:
        LOG.info("========================")
        LOG.info("Checking: %s", prod)
        engine = cfg_sql_server.create_engine()
        config_session = sessionmaker(bind=engine)
        sess = config_session()

        product = sess.query(ORMProduct).filter(
                ORMProduct.endpoint == prod).first()
        db = database.SQLServer.from_connection_string(product.connection,
                                                       RUN_META,
                                                       migration_root,
                                                       interactive=False,
                                                       env=environ)

        db_status = db.connect()

        msg = database_status.db_status_msg.get(db_status,
                                                'Unknown database status')

        LOG.info(msg)
        if db_status == DBStatus.SCHEMA_MISSING:
            question = 'Do you want to initialize a new schema for ' \
                        + product.endpoint + '? Y(es)/n(o) '
            if force_upgrade or env.get_user_input(question):
                ret = db.connect(init=True)
                msg = database_status.db_status_msg.get(
                    ret, 'Unknown database status')
                LOG.info(msg)
            else:
                LOG.info("No schema initialization was done.")

        elif db_status == DBStatus.SCHEMA_MISMATCH_OK:
            question = 'Do you want to upgrade to new schema for ' \
                        + product.endpoint + '? Y(es)/n(o) '
            if force_upgrade or env.get_user_input(question):
                LOG.info("Upgrading schema ...")
                ret = db.upgrade()
                LOG.info("Done.")
                msg = database_status.db_status_msg.get(
                    ret, 'Unknown database status')
                LOG.info(msg)
            else:
                LOG.info("No schema migration was done.")

        sess.commit()
        sess.close()
        engine.dispose()
        LOG.info("========================")
    return 0


def kill_process_tree(parent_pid, recursive=False):
    """Stop the process tree try it gracefully first.

    Try to stop the parent and child processes gracefuly
    first if they do not stop in time send a kill signal
    to every member of the process tree.

    There is a similar function in the analyzer part please
    consider to update that in case of changing this.
    """
    proc = psutil.Process(parent_pid)
    children = proc.children(recursive)

    # Send a SIGTERM (Ctrl-C) to the main process
    proc.terminate()

    # If children processes don't stop gracefully in time,
    # slaughter them by force.
    _, still_alive = psutil.wait_procs(children, timeout=5)
    for p in still_alive:
        p.kill()

    # Wait until this process is running.
    n = 0
    timeout = 10
    while proc.is_running():
        if n > timeout:
            LOG.warning("Waiting for process %s to stop has been timed out"
                        "(timeout = %s)! Process is still running!",
                        parent_pid, timeout)
            break

        time.sleep(1)
        n += 1


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
        for instance in instances:
            if not instances_on_multiple_hosts:
                rows.append((instance['workspace'], str(instance['port'])))
            else:
                rows.append((instance['workspace'],
                             instance['hostname']
                             if instance['hostname'] != socket.gethostname()
                             else '',
                             str(instance['port'])))

        print("Your running CodeChecker servers:")
        print(twodim.to_str('table', head, rows))
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
                kill_process_tree(i['pid'])
                LOG.info("Stopped CodeChecker server running on port %s "
                         "in workspace %s (PID: %s)",
                         i['port'], i['workspace'], i['pid'])
            except Exception:
                # Let the exception come out if the commands fail
                LOG.error("Couldn't stop process PID #%s", str(i['pid']))
                raise


def __reload_config(args):
    """
    Sends the CodeChecker server process a SIGHUP signal, causing it to
    reread it's configuration files.
    """
    for i in instance_manager.get_instances():
        if i['hostname'] != socket.gethostname():
            continue

        # A RELOAD only reloads the server associated with the given workspace
        # and view-port.
        if 'reload' in args and \
                not (i['port'] == args.view_port and
                     os.path.abspath(i['workspace']) ==
                     os.path.abspath(args.config_directory)):
            continue

        try:
            if sys.platform != "win32":
                os.kill(i['pid'], signal.SIGHUP)
        except Exception:
            LOG.error("Couldn't reload configuration file for process PID #%s",
                      str(i['pid']))
            raise


def is_localhost(address):
    """
    Check if address is one of the valid values and try to get the
    IP-addresses from the system.
    """

    valid_values = ['localhost', '0.0.0.0', '*', '::1']

    try:
        valid_values.append(socket.gethostbyname('localhost'))
    except socket.herror:
        LOG.debug("Failed to get IP address for localhost.")

    try:
        valid_values.append(socket.gethostbyname(socket.gethostname()))
    except (socket.herror, socket.gaierror):
        LOG.debug("Failed to get IP address for hostname '%s'",
                  socket.gethostname())

    return address in valid_values


def server_init_start(args):
    """
    Start or manage a CodeChecker report server.
    """

    if 'list' in args or 'stop' in args or 'stop_all' in args:
        __instance_management(args)
        sys.exit(0)

    if 'reload' in args:
        __reload_config(args)
        sys.exit(0)

    # Actual server starting from this point.
    if not host_check.check_zlib():
        raise Exception("zlib is not available on the system!")

    # WARNING
    # In case of SQLite args.dbaddress default value is used
    # for which the is_localhost should return true.
    if is_localhost(args.dbaddress) and \
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

    context = webserver_context.get_context()
    context.codechecker_workspace = args.config_directory
    context.db_username = args.dbusername

    environ = env.extend(context.path_env_extra,
                         context.ld_lib_path_extra)

    cfg_sql_server = database.SQLServer.from_cmdline_args(
        vars(args), CONFIG_META, context.config_migration_root,
        interactive=True, env=environ)

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

    force_upgrade = True if 'force_upgrade' in args else False

    if db_status == DBStatus.SCHEMA_MISMATCH_OK:
        LOG.debug("Configuration database schema mismatch.")
        LOG.debug("Schema upgrade is possible.")
        LOG.warning("Please note after migration only "
                    "newer CodeChecker versions can be used "
                    "to start the server")
        LOG.warning("It is advised to make a full backup of your "
                    "configuration database")

        LOG.warning(cfg_sql_server.get_db_location())

        question = 'Do you want to upgrade to the new schema?' \
                   ' Y(es)/n(o) '
        if force_upgrade or env.get_user_input(question):
            print("Upgrading schema ...")
            ret = cfg_sql_server.upgrade()
            msg = database_status.db_status_msg.get(
                ret, 'Unknown database status')
            print(msg)
            if ret != DBStatus.OK:
                LOG.error("Schema migration failed")
                sys.exit(ret)
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
            ret = __db_status_check(cfg_sql_server, context.migration_root,
                                    environ, args.status)
            sys.exit(ret)
    except AttributeError:
        LOG.debug('Status was not in the arguments.')

    try:
        if args.product_to_upgrade:
            ret = __db_migration(cfg_sql_server, context.migration_root,
                                 environ, args.product_to_upgrade,
                                 force_upgrade)
            sys.exit(ret)
    except AttributeError:
        LOG.debug('Product upgrade was not in the arguments.')

    # Create the main database link from the arguments passed over the
    # command line.
    cfg_dir = os.path.abspath(args.config_directory)
    default_product_path = os.path.join(cfg_dir, 'Default.sqlite')
    create_default_product = 'sqlite' in args and \
                             not os.path.exists(default_product_path)

    if create_default_product:
        # Create a default product and add it to the configuration database.

        LOG.debug("Create default product...")
        LOG.debug("Configuring schema and migration...")

        prod_server = database.SQLiteDatabase(
            default_product_path, RUN_META,
            context.run_migration_root, environ)

        LOG.debug("Checking 'Default' product database.")
        db_status = prod_server.connect()
        if db_status != DBStatus.MISSING:
            db_status = prod_server.connect(init=True)
            LOG.debug(database_status.db_status_msg.get(db_status))
            if db_status != DBStatus.OK:
                LOG.error("Failed to configure default product")
                sys.exit(1)

        product_conn_string = prod_server.get_connection_string()

        server.add_initial_run_database(
            cfg_sql_server, product_conn_string)

        LOG.info("Product 'Default' at '%s' created and set up.",
                 default_product_path)

    prod_statuses = check_product_db_status(cfg_sql_server,
                                            context.run_migration_root,
                                            environ)

    upgrade_available = {}
    for k, v in prod_statuses.items():
        db_status, _, _, _ = v
        if db_status == DBStatus.SCHEMA_MISMATCH_OK or \
                db_status == DBStatus.SCHEMA_MISSING:
            upgrade_available[k] = v

    if upgrade_available:
        print_prod_status(prod_statuses)
        LOG.warning("Multiple products can be upgraded, make a backup!")
        __db_migration(cfg_sql_server, context.run_migration_root,
                       environ, 'all', force_upgrade)

    prod_statuses = check_product_db_status(cfg_sql_server,
                                            context.run_migration_root,
                                            environ)
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
        if not env.get_user_input(msg):
            sys.exit(1)

    # Start database viewer.
    package_data = {'www_root': context.www_root,
                    'doc_root': context.doc_root,
                    'version': context.package_git_tag}

    try:
        server.start_server(args.config_directory,
                            package_data,
                            args.view_port,
                            cfg_sql_server,
                            args.listen_address,
                            'force_auth' in args,
                            args.skip_db_cleanup,
                            context,
                            environ)
    except socket.error as err:
        if err.errno == errno.EADDRINUSE:
            LOG.error("Server can't be started, maybe port number (%s) is "
                      "already used. Check the connection parameters. Use "
                      "the option '-p 0' to find a free port automatically.",
                      args.view_port)
            sys.exit(1)
        else:
            raise


def main(args):
    """
    Setup a logger server based on the configuration and
    manage the CodeChecker server.
    """
    with logger.LOG_CFG_SERVER(args.verbose if 'verbose' in args else None):
        try:
            cmd_config.check_config_file(args)
        except FileNotFoundError as fnerr:
            LOG.error(fnerr)
            sys.exit(1)
        server_init_start(args)
