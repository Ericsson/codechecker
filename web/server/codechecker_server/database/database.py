# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Database connection handling to a database backend.
"""
from abc import ABCMeta, abstractmethod
import os
import subprocess

from alembic import command, config
from alembic import script
from alembic import migration

from alembic.util import CommandError
import sqlalchemy
from sqlalchemy import event
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from codechecker_api_shared.ttypes import DBStatus

from codechecker_common.logger import get_logger

from codechecker_web.shared import host_check, pgpass


LOG = get_logger('system')


def call_command(cmd, env=None, cwd=None):
    """ Call an external cmd and return with (output, return_code)."""

    try:
        LOG.debug('Run %s', ' '.join(cmd))
        out = subprocess.check_output(cmd,
                                      env=env,
                                      stderr=subprocess.STDOUT,
                                      cwd=cwd,
                                      encoding="utf-8",
                                      errors="ignore")
        LOG.debug(out)
        return out, 0
    except subprocess.CalledProcessError as ex:
        LOG.debug('Running command "%s" Failed.', ' '.join(cmd))
        LOG.debug(str(ex.returncode))
        LOG.debug(ex.output)
        return ex.output, ex.returncode
    except OSError as oerr:
        LOG.warning(oerr.strerror)
        return oerr.strerror, oerr.errno


class DBSession:
    """
    Requires a session maker object and creates one session which can be used
    in the context.

    The session will be automatically closed, but commiting must be done
    inside the context.
    """
    def __init__(self, session_maker):
        self.__session = None
        self.__session_maker = session_maker

    def __enter__(self):
        # create new session
        self.__session = self.__session_maker()
        return self.__session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__session:
            self.__session.close()


class DBContext:
    """
    Simple helper class to setup and sql engine, a database session
    and a connection.

    NOTE: The error property should be always checked inside the
    with statement to verify that the engine/connection/session
    setup was successful.
    """

    def __init__(self, sql_server):
        self.sql_server = sql_server
        self.db_engine = None
        self.db_session = None
        self.db_connection = None
        self.db_error = None

    def __enter__(self):
        self.db_error = None
        try:
            self.db_engine = self.sql_server.create_engine()
            self.db_session = sessionmaker(bind=self.engine)()
            self.db_connection = self.db_session.connection()
        except Exception as ex:
            LOG.debug("Connection error")
            LOG.debug(ex)
            self.db_error = DBStatus.FAILED_TO_CONNECT

        return self

    @property
    def error(self):
        # Indicate that there is some problem with the
        # database setup.
        return self.db_error

    @property
    def engine(self):
        # Get the configured engine.
        return self.db_engine

    @property
    def connection(self):
        # Get the configured connection.
        return self.db_connection

    @property
    def session(self):
        # Get the configured session.
        return self.db_session

    def __exit__(self, *args):
        if self.db_session:
            self.db_session.close()
        if self.db_connection:
            self.db_connection.close()
        if self.db_engine:
            self.db_engine.dispose()


class SQLServer(metaclass=ABCMeta):
    """
    Abstract base class for database server handling. An SQLServer instance is
    responsible for the connection management towards the database.

    SQLServer implementations are created via SQLServer.from_cmdline_args().

    How to add a new database server implementation:
        1, Derive from SQLServer and implement the abstract methods
        2, Add/modify some command line options in CodeChecker.py
        3, Modify SQLServer.from_cmdline_args() in order to create an
           instance of the new server type if needed
    """

    def __init__(self, model_meta, migration_root):
        """
        Sets self.migration_root. migration_root should be the path to the
        alembic migration scripts.

        Also sets the created class' model identifier to the given meta dict.
        """

        self.__model_meta = model_meta
        self.migration_root = migration_root

    def _create_schema(self):
        """
        Creates the database schema if needed.
        The database server has to be started before this method is called.
        """

        try:
            with DBContext(self) as db:
                if db.error:
                    return db.error

                cfg = config.Config()
                cfg.set_main_option("script_location", self.migration_root)
                cfg.attributes["connection"] = db.connection

                mcontext = migration.MigrationContext.configure(db.connection)
                database_schema_revision = mcontext.get_current_revision()
                LOG.debug('Schema revision in the database: ' +
                          str(database_schema_revision))

                if database_schema_revision:
                    LOG.debug('Database schema was found.'
                              ' No need to initialize new.')
                else:
                    LOG.debug('No schema was detected in the database.')
                    LOG.debug('Initializing new ...')
                    command.upgrade(cfg, "head")
                    db.session.commit()
                    LOG.debug('Done.')
                    return True

                return True

        except sqlalchemy.exc.SQLAlchemyError as alch_err:
            LOG.error(str(alch_err))
            return False

        except Exception as ex:
            LOG.error("Failed to create initial database schema")
            LOG.error(ex)
            return False

    def get_schema_version(self):
        """
        Return the schema version from the database or a
        database status error code.
        """
        try:
            with DBContext(self) as db:
                if db.error:
                    return db.error

                mcontext = migration.MigrationContext.configure(db.connection)
                database_schema_revision = mcontext.get_current_revision()
                LOG.debug("Schema revision in the database: %s",
                          str(database_schema_revision))

                if database_schema_revision is None:
                    LOG.debug("Database schema should have been created!")
                    return DBStatus.SCHEMA_MISSING

                return database_schema_revision

        except sqlalchemy.exc.SQLAlchemyError as alch_err:
            LOG.debug(str(alch_err))
            return DBStatus.FAILED_TO_CONNECT

    def check_schema(self):
        """
        Checks the database schema for schema mismatch.
        The database server has to be started before this method is called.
        """

        try:
            with DBContext(self) as db:
                if db.error:
                    return db.error

                cfg = config.Config()
                cfg.set_main_option("script_location", self.migration_root)
                cfg.attributes["connection"] = db.connection

                scriptt = script.ScriptDirectory.from_config(cfg)
                mcontext = migration.MigrationContext.configure(
                    db.connection)
                database_schema_revision = mcontext.get_current_revision()
                LOG.debug("Schema revision in the database: %s",
                          str(database_schema_revision))

                if database_schema_revision is None:
                    LOG.debug("Database schema should have been created!")
                    return DBStatus.SCHEMA_MISSING

                LOG.debug("Checking schema versions in the package.")
                schema_config_head = scriptt.get_current_head()

                if database_schema_revision != schema_config_head:
                    LOG.debug("Database schema mismatch detected "
                              "between the package and the database")
                    LOG.debug("Checking if automatic upgrade is possible.")
                    all_revs = [rev.revision for rev in
                                scriptt.walk_revisions()]

                    if database_schema_revision not in all_revs:
                        LOG.debug("Automatic schema upgrade is not possible!")
                        LOG.debug("Please re-check your database and"
                                  "CodeChecker versions!")
                        return DBStatus.SCHEMA_MISMATCH_NO

                    # There is a schema mismatch.
                    return DBStatus.SCHEMA_MISMATCH_OK
                else:
                    LOG.debug("Schema in the package and"
                              " in the database is the same.")
                    LOG.debug("No schema modification is needed.")
                    return DBStatus.OK

        except sqlalchemy.exc.SQLAlchemyError as alch_err:
            LOG.debug(str(alch_err))
            return DBStatus.FAILED_TO_CONNECT
        except CommandError as cerr:
            LOG.debug("Database schema and CodeChecker is incompatible. "
                      "Please update CodeChecker.")
            LOG.debug(str(cerr))
            return DBStatus.SCHEMA_MISMATCH_NO

    def upgrade(self):
        """
        Upgrade database db schema.

        Checks the database schema for schema mismatch.
        The database server has to be started before this method is called.

        This method runs an alembic upgrade to HEAD.

        """

        # another safety check before we initialize or upgrade the schema
        ret = self.check_schema()

        migration_ok = [DBStatus.SCHEMA_MISMATCH_OK,
                        DBStatus.SCHEMA_MISSING]
        if ret not in migration_ok:
            # schema migration is not possible
            return ret

        try:
            with DBContext(self) as db:
                if db.error:
                    return db.error

                LOG.debug("Update/create database schema for %s",
                          self.__model_meta['identifier'])
                LOG.debug("Creating new database session")

                cfg = config.Config()
                cfg.set_main_option("script_location", self.migration_root)
                cfg.attributes["connection"] = db.connection
                command.upgrade(cfg, "head")
                db.session.commit()

                LOG.debug("Upgrading database schema: Done")
                return DBStatus.OK

        except sqlalchemy.exc.SQLAlchemyError as alch_err:
            LOG.error(str(alch_err))
            return DBStatus.SCHEMA_UPGRADE_FAILED

        except CommandError as cerr:
            LOG.debug(str(cerr))
            return DBStatus.SCHEMA_UPGRADE_FAILED

    @abstractmethod
    def connect(self, init=False):
        """
        Starts the database server and initializes the database server.

        On init == True, this it also initializes the database data and schema
        if needed.

        """
        pass

    @abstractmethod
    def get_connection_string(self):
        """
        Returns the connection string for SQLAlchemy.

        DO NOT LOG THE CONNECTION STRING BECAUSE IT MAY CONTAIN THE PASSWORD
        FOR THE DATABASE!
        """
        pass

    @abstractmethod
    def get_db_location(self):
        """
        Returns the database location.

        DATABASE USERNAME AND PASSWORD SHOULD NOT BE RETURNED HERE!
        """
        pass

    def get_model_identifier(self):
        return self.__model_meta['identifier']

    def _register_engine_hooks(self, engine):
        """
        This method registers hooks, if needed, related to the engine created
        by create_engine.
        """
        pass

    def create_engine(self):
        """
        Creates a new SQLAlchemy engine.
        """

        if make_url(self.get_connection_string()).drivername == \
                'sqlite+pysqlite':
            # FIXME: workaround for locking errors
            # FIXME: why is the connection used by multiple threads
            # is that a problem ??? do we need some extra locking???
            engine = sqlalchemy.create_engine(self.get_connection_string(),
                                              encoding='utf8',
                                              connect_args={'timeout': 600,
                                              'check_same_thread': False},
                                              poolclass=NullPool)
        else:
            engine = sqlalchemy.create_engine(self.get_connection_string(),
                                              encoding='utf8',
                                              poolclass=NullPool)

        self._register_engine_hooks(engine)
        return engine

    @staticmethod
    def connection_string_to_args(connection_string):
        """
        Convert the given connection string to an argument dict.

        !CAREFUL! This dict MIGHT contain a database password which SHOULD NOT
        be given to users!
        """

        url = make_url(connection_string)

        # Create an args for from_cmdline_args.
        args = {}
        if 'postgresql' in url.drivername:
            args['postgresql'] = True
            args['dbaddress'] = url.host
            args['dbport'] = url.port
            args['dbusername'] = url.username
            args['dbpassword'] = url.password
            args['dbname'] = url.database
        elif 'sqlite' in url.drivername:
            args['postgresql'] = False
            args['sqlite'] = url.database

        return args

    @staticmethod
    def from_connection_string(connection_string, model_meta, migration_root,
                               interactive=False, env=None):
        """
        Normally only this method is called form outside of this module in
        order to instance the proper server implementation.

        Parameters:
            args: the dict of database arguments
            model_meta: the meta identifier of the database model to use
            migration_root: path to the database migration scripts
            env: a run environment dictionary.
        """

        args = SQLServer.connection_string_to_args(connection_string)
        return SQLServer.from_cmdline_args(args, model_meta, migration_root,
                                           interactive, env)

    @staticmethod
    def from_cmdline_args(args, model_meta, migration_root,
                          interactive=False, env=None):
        """
        Normally only this method is called form outside of this module in
        order to instance the proper server implementation.

        Parameters:
            args: the command line arguments from CodeChecker.py, but as a
              dictionary (if argparse.Namespace, use vars(args)).
            model_meta: the meta identifier of the database model to use
            migration_root: path to the database migration scripts
            interactive: whether or not the database connection can be
              interactive on the server's shell.
            env: a run environment dictionary.
        """

        if not host_check.check_sql_driver(args['postgresql']):
            LOG.error("The selected SQL driver is not available!")
            raise IOError("The SQL driver to be used is not available!")

        if args['postgresql']:
            LOG.debug("Using PostgreSQL:")
            return PostgreSQLServer(model_meta,
                                    migration_root,
                                    args['dbaddress'],
                                    args['dbport'],
                                    args['dbusername'],
                                    args['dbname'],
                                    password=args['dbpassword']
                                    if 'dbpassword' in args else None,
                                    interactive=interactive,
                                    run_env=env)
        else:
            LOG.debug("Using SQLite:")
            data_file = os.path.abspath(args['sqlite'])
            LOG.debug("Database at %s", data_file)
            return SQLiteDatabase(data_file, model_meta,
                                  migration_root, run_env=env)


class PostgreSQLServer(SQLServer):
    """
    Handler for PostgreSQL.
    """

    def __init__(self, model_meta, migration_root, host, port, user, database,
                 password=None, interactive=False, run_env=None):
        super(PostgreSQLServer, self).__init__(model_meta, migration_root)

        self.host = host
        self.port = port
        self.user = user
        self.database = database
        self.password = password
        self.interactive = interactive
        self.run_env = run_env

    def _get_connection_string(self, database):
        """
        Helper method for getting the connection string for the given database.

        database -- The user can force the database name in the returning
        connection string. However the password, if any, provided e.g. in a
        .pgpass file will be queried based on the database name which is given
        as a command line argument, even if it has a default value. The reason
        is that sometimes a connection with a common database name is needed,
        (e.g. 'postgres'), which requires less user permission.
        """

        driver = host_check.get_postgresql_driver_name()
        password = self.password
        if driver == 'pg8000' and not password:
            pfilepath = os.environ.get('PGPASSFILE')
            if pfilepath:
                password = pgpass.get_password_from_file(pfilepath,
                                                         self.host,
                                                         str(self.port),
                                                         self.database,
                                                         self.user)

        extra_args = {}
        if driver == "psycopg2":
            extra_args = {'client_encoding': 'utf8'}
        return str(URL('postgresql+' + driver,
                       username=self.user,
                       password=password,
                       host=self.host,
                       port=str(self.port),
                       database=database,
                       query=extra_args))

    def connect(self, init=False):
        """
        Connect to a PostgreSQL instance with given path, host and port.
        """

        LOG.debug("Connecting to database...")

        LOG.debug("Checking if database is running at [%s:%s]",
                  self.host, str(self.port))

        if self.user:
            # Try to connect to a specific database
            # with a specific user.
            check_db = ['psql',
                        '-h', self.host,
                        '-p', str(self.port),
                        '-U', self.user,
                        '-d', self.database,
                        '-c', 'SELECT version();']
        else:
            # Try to connect with the default settings.
            check_db = ['psql',
                        '-h', self.host,
                        '-p', str(self.port),
                        '-c', 'SELECT version();']

        if not self.interactive:
            # Do not prompt for password in non-interactive mode.
            check_db.append('--no-password')

        # If the user has a password pre-specified, use that for the
        # 'psql' call!
        env = self.run_env if self.run_env else os.environ
        env = env.copy()
        if self.password:
            env['PGPASSWORD'] = self.password

        err, code = call_command(check_db, env)

        if code:
            LOG.debug(err)
            return DBStatus.FAILED_TO_CONNECT

        if init:
            if not self._create_schema():
                return DBStatus.SCHEMA_INIT_ERROR

        return self.check_schema()

    def get_connection_string(self):
        return self._get_connection_string(self.database)

    def get_db_location(self):
        return self.host + ":" + str(self.port) + "/" + self.database


class SQLiteDatabase(SQLServer):
    """
    Handler for SQLite.
    """

    def __init__(self, data_file, model_meta, migration_root, run_env=None):
        super(SQLiteDatabase, self).__init__(model_meta, migration_root)

        self.dbpath = data_file
        self.run_env = run_env

    def _register_engine_hooks(self, engine):
        """
        SQLite databases need FOREIGN KEYs to be enabled, which is handled
        through this connection hook.
        """
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        event.listen(engine, 'connect', _set_sqlite_pragma)

    def connect(self, init=False):
        if init:
            if not self._create_schema():
                LOG.error("Failed to create schema")
                return DBStatus.SCHEMA_INIT_ERROR

        return self.check_schema()

    def get_connection_string(self):
        return str(URL('sqlite+pysqlite', None, None, None, None, self.dbpath))

    def get_db_location(self):
        return self.dbpath


def conv(filter_value):
    """
    Convert * to % got from clients for the database queries.
    """
    if filter_value is None:
        return '%'
    return filter_value.replace('*', '%')


def escape_like(string, escape_char='*'):
    """Escape the string parameter used in SQL LIKE expressions."""
    return string.replace(escape_char, escape_char * 2) \
                 .replace('%', escape_char + '%') \
                 .replace('_', escape_char + '_')
