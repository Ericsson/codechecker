# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Database server handling for the server's configuration database.
"""

# TODO: Merge with run_database.

from abc import ABCMeta, abstractmethod
import os
import sys
import threading

from alembic import command, config
from alembic.util import CommandError
import sqlalchemy
from sqlalchemy import event
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.sql.elements import quoted_name

from libcodechecker import host_check
from libcodechecker import pgpass
from libcodechecker import util
from libcodechecker.logger import LoggerFactory

from config_db_model import CC_META
from config_db_model import DBVersion

LOG = LoggerFactory.get_new_logger('CONFIG DB HANDLER')


class SQLServer(object):
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

    __metaclass__ = ABCMeta

    def __init__(self, migration_root):
        """
        Sets self.migration_root. migration_root should be the path to the
        alembic migration scripts.
        """

        self.migration_root = migration_root

    def _create_or_update_schema(self, use_migration=True):
        """
        Creates or updates the database schema. The database server has to be
        started before this method is called.

        If use_migration is True, this method runs an alembic upgrade to HEAD.

        In the False case, there is no migration support and only SQLAlchemy
        meta data is used for schema creation.

        On error sys.exit(1) is called.
        """

        try:
            db_uri = self.get_connection_string()
            engine = SQLServer.create_engine(db_uri)

            LOG.debug("Update/create database schema")
            if use_migration:
                LOG.debug("Creating new database session")
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
            LOG.debug("Update/create database schema: Done")
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
    def connect(self, db_version_info, init=False):
        """
        Starts the database server and initializes the database server.

        On init == True, this it also initializes the database data and schema
        if needed.

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
            return sqlalchemy.create_engine(
                connection_string,
                encoding='utf8',
                connect_args={'timeout': 600})
        else:
            return sqlalchemy.create_engine(connection_string,
                                            encoding='utf8')

    @staticmethod
    def from_cmdline_args(args, migration_root, env=None):
        """
        Normally only this method is called form outside of this module in
        order to instance the proper server implementation.

        Parameters:
            args: the command line arguments from CodeChecker.py
            migration_root: path to the database migration scripts
            env: a run environment dictionary.
        """

        if not host_check.check_sql_driver(args.postgresql):
            LOG.error("The selected SQL driver is not available!")
            sys.exit(1)

        if args.postgresql:
            LOG.debug("Using PostgreSQL:")
            return PostgreSQLServer(migration_root,
                                    args.dbaddress,
                                    args.dbport,
                                    args.dbusername,
                                    args.dbname,
                                    run_env=env)
        else:
            LOG.debug("Using SQLite:")
            data_file = os.path.abspath(args.sqlite)
            LOG.debug("Database at " + data_file)
            return SQLiteDatabase(data_file, migration_root, run_env=env)

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
                LOG.error("No version information found in the database.")
                sys.exit(1)
            elif not db_version_info.is_compatible(version.major,
                                                   version.minor):
                LOG.error("Version mismatch. Expected database version: " +
                          str(db_version_info))
                version_from_db = 'v' + str(version.major) + '.' + str(
                    version.minor)
                LOG.error("Version from the database is: " + version_from_db)
                LOG.error("Please update your database.")
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
        LOG.debug("Adding DB version: " + str(expected))

        session.add(DBVersion(expected[0], expected[1]))
        session.commit()

        if engine:
            engine.dispose()

        LOG.debug("Adding DB version done!")


class PostgreSQLServer(SQLServer):
    """
    Handler for PostgreSQL.
    """

    def __init__(self, migration_root, host, port, user, database,
                 password=None, run_env=None):
        super(PostgreSQLServer, self).__init__(migration_root)

        self.host = host
        self.port = port
        self.user = user
        self.database = database
        self.password = password
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

        extra_args = {'client_encoding': 'utf8'}
        return str(URL('postgresql+' + driver,
                       username=self.user,
                       password=password,
                       host=self.host,
                       port=str(self.port),
                       database=database,
                       query=extra_args))

    def connect(self, db_version_info, init=False):
        """
        Connect to a PostgreSQL instance with given path, host and port.
        """

        LOG.debug("Connecting to database...")

        LOG.debug("Checking if database is running at [{0}:{1}]"
                  .format(self.host, str(self.port)))

        check_db = ['psql',
                    '-h', self.host,
                    '-p', str(self.port),
                    '-U', self.user,
                    '-d', self.database,
                    '-c', 'SELECT version();']
        err, code = util.call_command(check_db, self.run_env)

        if code:
            LOG.error("Database is not running, or cannot be connected to.")
            LOG.error(err)
            sys.exit(1)

        add_version = False
        if init:
            add_version = not self.check_db_version(db_version_info)
            self._create_or_update_schema(use_migration=False)

        if add_version:
            self._add_version(db_version_info)

        LOG.debug("Done. Connected to database.")

    def get_connection_string(self):
        return self._get_connection_string(self.database)


class SQLiteDatabase(SQLServer):
    """
    Handler for SQLite.
    """

    def __init__(self, data_file, migration_root, run_env=None):
        super(SQLiteDatabase, self).__init__(migration_root)

        self.dbpath = data_file
        self.run_env = run_env

        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        event.listen(Engine, 'connect', _set_sqlite_pragma)

    def connect(self, db_version_info, init=False):
        if init:
            add_version = not self.check_db_version(db_version_info)
            self._create_or_update_schema(use_migration=False)
            if add_version:
                self._add_version(db_version_info)

        if not os.path.exists(self.dbpath):
            LOG.error("Database (%s) is missing!" % self.dbpath)
            sys.exit(1)

    def get_connection_string(self):
        return str(URL('sqlite+pysqlite', None, None, None, None, self.dbpath))
