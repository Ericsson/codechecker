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
from functools import partial
import os
import signal
import socket
import sys
import time
from typing import List, Optional, Tuple, cast

from alembic import config
from alembic import script
from alembic.util import CommandError
import psutil
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from codechecker_api_shared.ttypes import DBStatus

from codechecker_report_converter import twodim

from codechecker_common import arg, cmd_config, logger, util
from codechecker_common.compatibility.multiprocessing import Pool, cpu_count

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
                             "result related data, such as the database.")

    parser.add_argument('-f', '--config-directory',
                        type=str,
                        dest="config_directory",
                        required=False,
                        help="Directory where CodeChecker server should read "
                             "server-specific configuration (such as "
                             "authentication settings, TLS certificate"
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
        if any(psql_args_matching) and 'postgresql' not in args:
            parser.error(f"argument {psql_args_matching[0]}: not allowed "
                         "without argument --postgresql")
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

        # If config_directory is not specified, it will be the same
        # as the workspace directory.
        if not args.config_directory:
            args.config_directory = args.workspace

        # If sqlite path is not specified, it will be set to
        # workspace/config.sqlite
        if not args.sqlite:
            args.sqlite = os.path.join(args.workspace,
                                       'config.sqlite')

        # Convert relative sqlite file path to absolute.
        args.sqlite = os.path.abspath(args.sqlite)

        if 'postgresql' not in args:
            # Later called database modules need the argument to be actually
            # present, even though the default is suppressed in the optstring.
            setattr(args, 'postgresql', False)
        else:
            # If --postgresql is given, --sqlite is useless.
            delattr(args, 'sqlite')

        # Indicate in args that we are in instance manager mode.
        if "list" in args or "stop" in args or "stop_all" in args:
            setattr(args, "instance_manager", True)

        # Log directories
        LOG.info(f"Workspace directory: {args.workspace}")
        LOG.info(f"Config directory: {args.config_directory}")

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

    products: List[ORMProduct] = []
    try:
        products = sess.query(ORMProduct) \
            .order_by(ORMProduct.endpoint.asc()) \
            .all()
    except Exception as ex:
        LOG.debug(ex)
        LOG.error("Failed to get product configurations from the database.")
        LOG.error("Please check your command arguments.")
        sys.exit(1)
    finally:
        # sys.exit raises SystemExit, which still performs finally clauses!
        sess.close()
        engine.dispose()

    package_schema = get_schema_version_from_package(migration_root)

    db_errors = [DBStatus.FAILED_TO_CONNECT,
                 DBStatus.MISSING,
                 DBStatus.SCHEMA_INIT_ERROR,
                 DBStatus.SCHEMA_MISSING]

    prod_status = {}
    for pd in products:
        db = database.SQLServer.from_connection_string(pd.connection,
                                                       pd.endpoint,
                                                       RUN_META,
                                                       migration_root,
                                                       interactive=False,
                                                       env=environ)
        db_location = db.get_db_location()

        try:
            status = db.connect()
            s_ver = db.get_schema_version()
            if s_ver in db_errors:
                s_ver = None
            prod_status[pd.endpoint] = (status, s_ver, package_schema,
                                        db_location)
        except Exception:
            LOG.error("Unable to get the status for product '%s', "
                      "considering as if the connection failed.",
                      pd.endpoint)
            prod_status[pd.endpoint] = (DBStatus.FAILED_TO_CONNECT, None,
                                        package_schema, db_location)

    return prod_status


def __db_status_check(cfg_sql_server, migration_root, environ,
                      product_name=None) -> int:
    """
    Check and print database statuses for the given product.
    """
    if not product_name:
        return 0

    LOG.debug("Checking database status for %s product.", product_name)

    prod_statuses = check_product_db_status(cfg_sql_server, migration_root,
                                            environ)

    if product_name != "all":
        avail = prod_statuses.get(product_name)
        if not avail:
            LOG.error("No product was found with this endpoint: %s",
                      str(product_name))
            return 1

        prod_statuses = {k: v for k, v in prod_statuses.items()
                         if k == product_name}

    print_prod_status(prod_statuses)
    return 0


class NonExistentProductError(Exception):
    def __init__(self, product_name):
        super().__init__(f"Non-existent product '{product_name}'")
        self.product_name = product_name


def __db_migration(migration_root,
                   environ,
                   endpoint: str,
                   connection_string: str,
                   init_instead_of_upgrade: bool) -> DBStatus:
    try:
        db = database.SQLServer.from_connection_string(connection_string,
                                                       endpoint,
                                                       RUN_META,
                                                       migration_root,
                                                       interactive=False,
                                                       env=environ)
        if init_instead_of_upgrade:
            LOG.info("[%s] Initialising...", endpoint)
            status = db.connect(init=True)
        else:
            LOG.info("[%s] Upgrading...", endpoint)
            db.connect(init=False)
            status = db.upgrade()

        status_str = database_status.db_status_msg.get(
            status, "Unknown database status")
        LOG.info("[%s] Done %s. %s", endpoint,
                 "initialising" if init_instead_of_upgrade else "upgrading",
                 status_str)
        return status
    except (CommandError, SQLAlchemyError):
        LOG.error("A database error occurred during the init/migration of "
                  "'%s'", endpoint)
        import traceback
        traceback.print_exc()
        return DBStatus.SCHEMA_INIT_ERROR if init_instead_of_upgrade \
            else DBStatus.SCHEMA_UPGRADE_FAILED
    except Exception as e:
        LOG.error("A generic error '%s' occurred during the init/migration "
                  "of '%s'", str(type(e)), endpoint)
        import traceback
        traceback.print_exc()
        return DBStatus.SCHEMA_INIT_ERROR if init_instead_of_upgrade \
            else DBStatus.SCHEMA_UPGRADE_FAILED


def __db_migration_multiple(
    cfg_sql_server, migration_root, environ,
    products_requested_for_upgrade: Optional[List[str]] = None,
    force_upgrade: bool = False
) -> int:
    """
    Migrates the schema for the product database
    ``products_requested_for_upgrade`` if specified, or all configured
    products (default).
    """
    LOG.info("Preparing schema upgrade for '%s'",
             "', '".join(products_requested_for_upgrade)
             if products_requested_for_upgrade else "<all products>")

    prod_statuses = check_product_db_status(cfg_sql_server,
                                            migration_root,
                                            environ)
    products_to_upgrade: List[str] = []
    for endpoint in (products_requested_for_upgrade or []):
        avail = prod_statuses.get(endpoint)
        if not avail:
            LOG.error("No product was found with endpoint '%s'", endpoint)
            return 1
        products_to_upgrade.append(endpoint)

    products_to_upgrade = list(prod_statuses.keys())
    products_to_upgrade.sort()

    def _get_migration_decisions() -> List[Tuple[str, str, bool]]:
        # The lifetime of the CONFIG database connection is scoped to this
        # helper function, as keeping it alive throughout PRODUCT migrations
        # could cause timeouts.
        cfg_engine = cfg_sql_server.create_engine()
        cfg_session_factory = sessionmaker(bind=cfg_engine)
        cfg_session = cfg_session_factory()

        scheduled_upgrades_or_inits: List[Tuple[str, str, bool]] = []
        for endpoint in products_to_upgrade:
            LOG.info("Checking: %s", endpoint)
            connection_str: Optional[str] = None

            try:
                product: Optional[ORMProduct] = cfg_session \
                    .query(ORMProduct.connection) \
                    .filter(ORMProduct.endpoint == endpoint) \
                    .one_or_none()
                if product is None:
                    raise NonExistentProductError(endpoint)

                connection_str = product.connection
            except NonExistentProductError as nepe:
                LOG.error("Attempted to upgrade product '%s', but it was not "
                          "found in the server's configuration database.",
                          nepe.product_name)
                continue
            except Exception:
                LOG.error("Failed to get the configuration for product '%s'",
                          endpoint)
                import traceback
                traceback.print_exc()
                continue

            try:
                db = database.SQLServer.from_connection_string(
                    cast(str, connection_str),
                    endpoint,
                    RUN_META,
                    migration_root,
                    interactive=False,
                    env=environ)
                db_status = db.connect()

                status_str = database_status.db_status_msg.get(
                    db_status, "Unknown database status")
                LOG.info(status_str)

                if db_status == DBStatus.SCHEMA_MISSING:
                    question = "Do you want to initialize a new schema for " \
                               f"'{endpoint}'" \
                               "? Y(es)/n(o) "
                    if force_upgrade or env.get_user_input(question):
                        LOG.info("[%s] Schema will be initialised...",
                                 endpoint)
                        scheduled_upgrades_or_inits.append(
                            (endpoint, cast(str, connection_str), True))
                    else:
                        LOG.info("[%s] No schema initialization will be done.",
                                 endpoint)
                elif db_status == DBStatus.SCHEMA_MISMATCH_OK:
                    question = f"Do you want to upgrade '{endpoint}' to new " \
                               "schema? Y(es)/n(o) "
                    if force_upgrade or env.get_user_input(question):
                        LOG.info("[%s] Schema will be upgraded...", endpoint)
                        scheduled_upgrades_or_inits.append(
                            (endpoint, cast(str, connection_str), False))
                    else:
                        LOG.info("[%s] No schema migration will be done.",
                                 endpoint)
            except (CommandError, SQLAlchemyError):
                LOG.error("A database error occurred during the preparation "
                          "for the init/migration of '%s'", endpoint)
                import traceback
                traceback.print_exc()
            except Exception as e:
                LOG.error("A generic error '%s' occurred during the "
                          "preparation for the init/migration of '%s'",
                          str(type(e)), endpoint)
                import traceback
                traceback.print_exc()

        cfg_session.close()
        cfg_engine.dispose()
        return scheduled_upgrades_or_inits

    LOG.warning("Please note after migration only newer CodeChecker versions "
                "can be used to start the server!")
    LOG.warning("It is advised to make a full backup of your run databases.")
    LOG.info("========================")
    scheduled_upgrades_or_inits = _get_migration_decisions()
    LOG.info("========================")

    if scheduled_upgrades_or_inits:
        failed_products: List[Tuple[str, DBStatus]] = []
        thr_count = util.clamp(1, len(scheduled_upgrades_or_inits),
                               cpu_count())
        with Pool(max_workers=thr_count) as executor:
            LOG.info("Initialising/upgrading products using %d concurrent "
                     "jobs...", thr_count)
            for product_cfg, return_status in \
                    zip(scheduled_upgrades_or_inits, executor.map(
                        # Bind the first 2 non-changing arguments of
                        # __db_migration, this is fixed for the execution.
                        partial(__db_migration, migration_root, environ),
                        # Transform List[Tuple[str, str, bool]] into an
                        # Iterable[Tuple[str], Tuple[str], Tuple[bool]],
                        # and immediately unpack it, thus providing the other
                        # 3 arguments of __db_migration as a parameter pack.
                        *zip(*scheduled_upgrades_or_inits))):
                if return_status != DBStatus.OK:
                    failed_products.append((product_cfg[0], return_status))

        if failed_products:
            prod_status = []
            for p in failed_products:
                status = database_status.db_status_msg.get(
                    p[1], "Unknown database status")
                prod_status.append(f"'{p[0]}' ({status})")

            LOG.error("The following products failed to upgrade: %s",
                      ', '.join(prod_status))
        else:
            LOG.info("Schema initialisation(s)/upgrade(s) executed "
                     "successfully.")
    LOG.info("========================")

    # This function always returns 0 if the upgrades were attempted, because
    # the server can start with some products that have failed to init/migrate.
    # It will just simply disallow the connection to those products.
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
                     os.path.abspath(args.workspace)):
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
                     os.path.abspath(args.workspace)):
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
        # Set the instance manager flag to True to be able watch for it during
        # logger setup.
        setattr(args, "instance_manager", True)
        __instance_management(args)
        sys.exit(0)

    if 'reload' in args:
        __reload_config(args)
        sys.exit(0)

    # Actual server starting from this point.
    if not host_check.check_zlib():
        raise ModuleNotFoundError("zlib is not available on the system!")

    # Make sure the SQLite file can be created if it not exists.
    if 'sqlite' in args and \
            not os.path.isdir(os.path.dirname(args.sqlite)):
        os.makedirs(os.path.dirname(args.sqlite))

    if 'force_auth' in args:
        LOG.info("'--force-authentication' was passed as a command-line "
                 "option. The server will ask for users to authenticate!")

    context = webserver_context.get_context()
    context.codechecker_workspace = args.workspace
    context.db_username = args.dbusername

    environ = env.extend(context.path_env_extra,
                         context.ld_lib_path_extra)

    cfg_sql_server = database.SQLServer.from_cmdline_args(
        vars(args), "config", CONFIG_META, context.config_migration_root,
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

    force_upgrade = 'force_upgrade' in args

    if db_status == DBStatus.SCHEMA_MISMATCH_OK:
        LOG.debug("Configuration database schema mismatch!")
        LOG.debug("Schema upgrade is possible.")
        LOG.warning("Please note after migration only newer CodeChecker "
                    "versions can be used to start the server!")
        LOG.warning("It is advised to make a full backup of your "
                    "configuration database!")
        LOG.warning(cfg_sql_server.get_db_location())

        question = "Do you want to upgrade to the new schema?" \
                   " Y(es)/n(o) "
        if force_upgrade or env.get_user_input(question):
            LOG.info("Upgrading schema ...")
            new_status = cfg_sql_server.upgrade()
            status_str = database_status.db_status_msg.get(
                new_status, "Unknown database status")
            LOG.info(status_str)
            if new_status != DBStatus.OK:
                LOG.error("Schema migration failed")
                sys.exit(new_status)
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
            ret = __db_status_check(cfg_sql_server,
                                    context.migration_root,
                                    environ,
                                    args.status)
            sys.exit(ret)
    except AttributeError:
        LOG.debug('Status was not in the arguments.')

    try:
        if args.product_to_upgrade:
            ret = __db_migration_multiple(
                cfg_sql_server,
                context.migration_root,
                environ,
                [args.product_to_upgrade]
                if args.product_to_upgrade != "all" else None,
                force_upgrade)
            sys.exit(ret)
    except AttributeError:
        LOG.debug('Product upgrade was not in the arguments.')

    # Create the main database link from the arguments passed over the
    # command line.
    workspace_dir = os.path.abspath(args.workspace)
    default_product_path = os.path.join(workspace_dir, 'Default.sqlite')
    create_default_product = 'sqlite' in args and \
                             not os.path.exists(default_product_path)

    if create_default_product:
        # Create a default product and add it to the configuration database.
        LOG.debug("Create default product...")
        LOG.debug("Configuring schema and migration...")

        prod_server = database.SQLiteDatabase(
            "Default", default_product_path, RUN_META,
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
        if db_status in (DBStatus.SCHEMA_MISMATCH_OK, DBStatus.SCHEMA_MISSING):
            upgrade_available[k] = v

    if upgrade_available:
        print_prod_status(prod_statuses)
        LOG.warning("Multiple products can be upgraded, make a backup!")
        __db_migration_multiple(cfg_sql_server,
                                context.run_migration_root,
                                environ,
                                None,
                                force_upgrade)

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
        LOG.error("There are some database issues.")
        if not force_upgrade:
            status_str = "Do you want to start the server? Y(es)/n(o) "
            if not env.get_user_input(status_str):
                sys.exit(1)

    # Start database viewer.
    package_data = {'www_root': context.www_root,
                    'doc_root': context.doc_root,
                    'version': context.package_git_tag}

    try:
        return server.start_server(args.config_directory,
                                   args.workspace,
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

    # Create workspace directory before logging is initialized.
    workspace = None
    if not hasattr(args, "instance_manager"):
        workspace = args.workspace

        if not os.path.exists(workspace):
            LOG.info("Creating non existing workspace directory: %s",
                     workspace)
            os.makedirs(workspace)

        if not os.path.exists(args.config_directory):
            LOG.info("Creating non existing config directory: %s",
                     args.config_directory)
            os.makedirs(args.config_directory)

    with logger.LogCfgServer(
        args.verbose if "verbose" in args else None, workspace=workspace
    ):
        try:
            cmd_config.check_config_file(args)
        except FileNotFoundError as fnerr:
            LOG.error(fnerr)
            sys.exit(1)
        server_init_start(args)
