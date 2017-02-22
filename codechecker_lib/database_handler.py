# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Database server handling.
"""

import atexit
import os
import subprocess
import sys
import time
from abc import ABCMeta, abstractmethod

import sqlalchemy
from alembic.util import CommandError
from alembic import command, config
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.sql.elements import quoted_name

from codechecker_lib import host_check
from codechecker_lib import pgpass
from codechecker_lib import util
from codechecker_lib import logger
from codechecker_lib.logger import LoggerFactory
from db_model.orm_model import CC_META
from db_model.orm_model import CreateSession
from db_model.orm_model import DBVersion

LOG = LoggerFactory.get_new_logger('DB_HANDLER')


class SQLServer(object):
    """
    Abstract base class for database server handling. An SQLServer instance is
    responsible for the initialization, starting, and stopping the database
    server, and also for connection string management.

    SQLServer implementations are created via SQLServer.from_cmdline_args().

    How to add a new database server implementation:
        1, Derive from SQLServer and implement the abstract methods
        2, Add/modify some command line options in CodeChecker.py
        3, Modify SQLServer.from_cmdline_args() in order to create an
           instance of the new server type if needed
    """

    __metaclass__ = ABCMeta

    def __init__(self, migration_root):
        """
        Sets self.migration_root. migration_root should be the path to the
        alembic migration scripts.
        """

        self.migration_root = migration_root

    def _create_or_update_schema(self, use_migration=True):
        """
        Creates or updates the database schema. The database server should be
        started before this method is called.

        If use_migration is True, this method runs an alembic upgrade to HEAD.

        In the False case, there is no migration support and only SQLAlchemy
        meta data is used for schema creation.

        On error sys.exit(1) is called.
        """

        try:
            db_uri = self.get_connection_string()
            engine = SQLServer.create_engine(db_uri)

            LOG.debug('Update/create database schema')
            if use_migration:
                LOG.debug('Creating new database session')
                session = CreateSession(engine)
                connection = session.connection()

                cfg = config.Config()
                cfg.set_main_option("script_location", self.migration_root)
                cfg.attributes["connection"] = connection
                command.upgrade(cfg, "head")

                session.commit()
            else:
                CC_META.create_all(engine)

            engine.dispose()
            LOG.debug('Update/create database schema done')
            return True

        except sqlalchemy.exc.SQLAlchemyError as alch_err:
            LOG.error(str(alch_err))
            sys.exit(1)
        except CommandError as cerr:
            LOG.error("Database schema and CodeChecker is incompatible."
                      "Please update CodeChecker.")
            LOG.debug(str(cerr))
            sys.exit(1)

    @abstractmethod
    def start(self, db_version_info, wait_for_start=True, init=False):
        """
        Starts the database server and initializes the database server.

        On wait_for_start == True, this method returns when the server is up
        and ready for connections. Otherwise it only starts the server and
        returns immediately.

        On init == True, this it also initializes the database data and schema
        if needed.

        On error sys.exit(1) should be called.
        """
        pass

    @abstractmethod
    def stop(self):
        """
        Terminates the database server.

        On error sys.exit(1) should be called.
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

    @staticmethod
    def create_engine(connection_string):
        """
        Creates a new SQLAlchemy engine.
        """

        if make_url(connection_string).drivername == 'sqlite+pysqlite':
            # FIXME: workaround for locking errors
            return sqlalchemy.create_engine(connection_string,
                                            encoding='utf8',
                                            connect_args={'timeout': 600})
        else:
            return sqlalchemy.create_engine(connection_string,
                                            encoding='utf8')

    @staticmethod
    def from_cmdline_args(args, workspace, migration_root, env=None):
        """
        Normally only this method is called form outside of this module in
        order to instance the proper server implementation.

        Parameters:
            args: the command line arguments from CodeChecker.py
            workspace: path to the CodeChecker workspace directory
            migration_root: path to the database migration scripts
            env: a run environment dictionary.
        """

        if not host_check.check_sql_driver(args.postgresql):
            LOG.error("The selected SQL driver is not available.")
            sys.exit(1)

        if args.postgresql:
            LOG.debug("Using PostgreSQLServer")
            return PostgreSQLServer(workspace,
                                    migration_root,
                                    args.dbaddress,
                                    args.dbport,
                                    args.dbusername,
                                    args.dbname,
                                    run_env=env)
        else:
            LOG.debug("Using SQLiteDatabase")
            return SQLiteDatabase(workspace, migration_root, run_env=env)

    def check_db_version(self, db_version_info, session=None):
        """
        Checks the database version and prints an error message on database
        version mismatch.

        - On mismatching or on missing version a sys.exit(1) is called.
        - On missing DBVersion table, it returns False
        - On compatible DB version, it returns True

        Parameters:
            db_version_info (db_version.DBVersionInfo): required database
                version.
            session: an open database session or None. If session is None, a
                new session is created.
        """

        try:
            dispose_engine = False
            if session is None:
                engine = SQLServer.create_engine(self.get_connection_string())
                dispose_engine = True
                session = CreateSession(engine)
            else:
                engine = session.get_bind()

            if not engine.has_table(quoted_name(DBVersion.__tablename__,
                                                True)):
                LOG.debug("Missing DBVersion table!")
                return False

            version = session.query(DBVersion).first()
            if version is None:
                # Version is not populated yet
                LOG.error('No version information found in the database.')
                sys.exit(1)
            elif not db_version_info.is_compatible(version.major,
                                                   version.minor):
                LOG.error('Version mismatch. Expected database version: ' +
                          str(db_version_info))
                version_from_db = 'v' + str(version.major) + '.' + str(
                    version.minor)
                LOG.error('Version from the database is: ' + version_from_db)
                LOG.error('Please update your database.')
                sys.exit(1)

            LOG.debug("Database version is compatible.")
            return True
        finally:
            session.commit()
            if dispose_engine:
                engine.dispose()

    def _add_version(self, db_version_info, session=None):
        """
        Fills the DBVersion table.
        """

        engine = None
        if session is None:
            engine = SQLServer.create_engine(self.get_connection_string())
            session = CreateSession(engine)

        expected = db_version_info.get_expected_version()
        LOG.debug('Adding DB version: ' + str(expected))

        session.add(DBVersion(expected[0], expected[1]))
        session.commit()

        if engine:
            engine.dispose()

        LOG.debug('Adding DB version done!')


class PostgreSQLServer(SQLServer):
    """
    Handler for PostgreSQL.
    """

    def __init__(self, workspace, migration_root, host, port, user, database,
                 password=None, run_env=None):
        super(PostgreSQLServer, self).__init__(migration_root)

        self.path = os.path.join(workspace, 'pgsql_data')
        self.host = host
        self.port = port
        self.user = user
        self.database = database
        self.password = password
        self.run_env = run_env
        self.workspace = workspace

        self.proc = None

    def _is_database_data_exist(self):
        """Check the PostgreSQL instance existence in a given path."""

        LOG.debug('Checking for database at ' + self.path)

        return os.path.exists(self.path) and \
            os.path.exists(os.path.join(self.path, 'PG_VERSION')) and \
            os.path.exists(os.path.join(self.path, 'base'))

    def _initialize_database_data(self):
        """Initialize a PostgreSQL instance with initdb. """

        LOG.debug('Initializing database at ' + self.path)

        init_db = ['initdb', '-U', self.user, '-D', self.path, '-E SQL_ASCII']

        err, code = util.call_command(init_db, self.run_env)
        # logger -> print error
        return code == 0

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

        port = str(self.port)
        driver = host_check.get_postgresql_driver_name()
        password = self.password
        if driver == 'pg8000' and not password:
            pfilepath = os.environ.get('PGPASSFILE')
            if pfilepath:
                password = pgpass.get_password_from_file(pfilepath,
                                                         self.host,
                                                         port,
                                                         self.database,
                                                         self.user)

        extra_args = {'client_encoding': 'utf8'}
        return str(URL('postgresql+' + driver,
                       username=self.user,
                       password=password,
                       host=self.host,
                       port=port,
                       database=database,
                       query=extra_args))

    def _wait_or_die(self):
        """
        Wait for database if the database process was stared
        with a different client. No polling is possible.
        """

        LOG.debug('Waiting for PostgreSQL')
        tries_count = 0
        max_try = 20
        timeout = 5
        while not self._is_running() and tries_count < max_try:
            tries_count += 1
            time.sleep(timeout)

            if tries_count >= max_try:
                LOG.error('Failed to start database.')
                sys.exit(1)

    def _create_database(self):
        try:
            LOG.debug('Creating new database if not exists.')

            db_uri = self._get_connection_string('postgres')
            engine = SQLServer.create_engine(db_uri)
            text = \
                "SELECT 1 FROM pg_database WHERE datname='%s'" % self.database
            if not bool(engine.execute(text).scalar()):
                conn = engine.connect()
                # From sqlalchemy documentation:
                # The psycopg2 and pg8000 dialects also offer the special level
                # AUTOCOMMIT.
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")
                conn.execute('CREATE DATABASE "%s"' % self.database)
                conn.close()

                LOG.debug('Database created: ' + self.database)

            LOG.debug('Database already exists: ' + self.database)

        except sqlalchemy.exc.SQLAlchemyError as alch_err:
            LOG.error('Failed to create database!')
            LOG.error(str(alch_err))
            sys.exit(1)

    def _is_running(self):
        """Is there PostgreSQL instance running on a given host and port."""

        LOG.debug('Checking if database is running at ' +
                  self.host + ':' + str(self.port))

        check_db = ['psql', '-U', self.user, '-c', 'SELECT version();',
                    '-p', str(self.port), '-h', self.host, '-d', 'postgres']
        err, code = util.call_command(check_db, self.run_env)
        return code == 0

    def start(self, db_version_info, wait_for_start=True, init=False):
        """
        Start a PostgreSQL instance with given path, host and port.
        Return with process instance.
        """

        LOG.debug('Starting/connecting to database.')
        if not self._is_running():
            if not util.is_localhost(self.host):
                LOG.info('Database is not running yet.')
                sys.exit(1)

            if not self._is_database_data_exist():
                if not init:
                    # The database does not exists.
                    LOG.error('Database data is missing!')
                    LOG.error('Please check your configuration!')
                    sys.exit(1)
                elif not self._initialize_database_data():
                    # The database does not exist and cannot create.
                    LOG.error('Database data is missing and '
                              'the initialization of a new failed!')
                    LOG.error('Please check your configuration!')
                    sys.exit(1)

            LOG.info('Starting database')
            LOG.debug('Starting database at ' + self.host + ':' + str(
                self.port) + ' ' + self.path)

            db_logfile = os.path.join(self.workspace, 'postgresql.log') \
                if LoggerFactory.get_log_level() == logger.DEBUG \
                else os.devnull
            self._db_log = open(db_logfile, 'wb')

            start_db = ['postgres', '-i',
                        '-D', self.path,
                        '-p', str(self.port),
                        '-h', self.host]
            self.proc = subprocess.Popen(start_db,
                                         bufsize=-1,
                                         env=self.run_env,
                                         stdout=self._db_log,
                                         stderr=subprocess.STDOUT)

        add_version = False
        if init:
            self._wait_or_die()
            self._create_database()
            add_version = not self.check_db_version(db_version_info)
            self._create_or_update_schema()
        elif wait_for_start:
            self._wait_or_die()
            add_version = not self.check_db_version(db_version_info)

        if add_version:
            self._add_version(db_version_info)

        atexit.register(self.stop)
        LOG.debug('Done')

    def stop(self):
        if self.proc:
            LOG.debug('Terminating database')
            self.proc.terminate()
            self._db_log.close()

    def get_connection_string(self):
        return self._get_connection_string(self.database)


class SQLiteDatabase(SQLServer):
    """
    Handler for SQLite.
    """

    def __init__(self, workspace, migration_root, run_env=None):
        super(SQLiteDatabase, self).__init__(migration_root)

        self.dbpath = os.path.join(workspace, 'codechecker.sqlite')
        self.run_env = run_env

        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        event.listen(Engine, 'connect', _set_sqlite_pragma)

    def start(self, db_version_info, wait_for_start=True, init=False):
        if init:
            add_version = not self.check_db_version(db_version_info)
            self._create_or_update_schema(use_migration=False)
            if add_version:
                self._add_version(db_version_info)

        if not os.path.exists(self.dbpath):
            # The database does not exists
            LOG.error('Database (%s) is missing!' % self.dbpath)
            sys.exit(1)

    def stop(self):
        pass

    def get_connection_string(self):
        return str(URL('sqlite+pysqlite', None, None, None, None, self.dbpath))
