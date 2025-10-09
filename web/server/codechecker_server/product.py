# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
The in-memory representation and access methods for querying and mutating a
"Product": a separate and self-contained database and entity containing
analysis results and associated information, which a CodeChecker server can
connect to.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import sessionmaker

from codechecker_api_shared.ttypes import DBStatus

from codechecker_common.logger import get_logger

from .database import database, db_cleanup
from .database.config_db_model import Product as DBProduct
from .database.database import DBSession
from .database.run_db_model import \
    IDENTIFIER as RUN_META, \
    Run, RunLock


LOG = get_logger("server")


class Product:
    """
    Represents a product, which is a distinct storage of analysis reports in
    a separate database (and database connection) with its own access control.
    """

    # The amount of SECONDS that need to pass after the last unsuccessful
    # connect() call so the next could be made.
    CONNECT_RETRY_TIMEOUT = 300

    def __init__(self, id_: int, endpoint: str, display_name: str,
                 connection_string: str, context, check_env):
        """
        Set up a new managed product object for the configuration given.
        """
        self.__id = id_
        self.__endpoint = endpoint
        self.__display_name = display_name
        self.__connection_string = connection_string
        self.__driver_name = None
        self.__context = context
        self.__check_env = check_env
        self.__engine = None
        self.__session = None
        self.__db_status = DBStatus.MISSING

        self.__last_connect_attempt = None

    @property
    def id(self):
        return self.__id

    @property
    def endpoint(self):
        """
        Returns the accessible URL endpoint of the product.
        """
        return self.__endpoint

    @property
    def name(self):
        """
        Returns the display name of the product.
        """
        return self.__display_name

    @property
    def session_factory(self):
        """
        Returns the session maker on this product's database engine which
        can be used to initiate transactional connections.
        """
        return self.__session

    @property
    def driver_name(self):
        """
        Returns the name of the sql driver (sqlite, postgres).
        """
        return self.__driver_name

    @property
    def db_status(self):
        """
        Returns the status of the database which belongs to this product.
        Call connect to update it.
        """
        return self.__db_status

    @property
    def last_connection_failure(self):
        """
        Returns the reason behind the last executed connection attempt's
        failure.
        """
        return self.__last_connect_attempt[1] if self.__last_connect_attempt \
            else None

    def connect(self, init_db=False):
        """
        Initiates the actual connection to the database configured for the
        product.

        Each time the connect is called the db_status is updated.
        """
        LOG.debug("Checking '%s' database.", self.endpoint)

        sql_server = database.SQLServer.from_connection_string(
            self.__connection_string,
            self.__endpoint,
            RUN_META,
            self.__context.run_migration_root,
            interactive=False,
            env=self.__check_env)

        if isinstance(sql_server, database.PostgreSQLServer):
            self.__driver_name = 'postgresql'
        elif isinstance(sql_server, database.SQLiteDatabase):
            self.__driver_name = 'sqlite'

        try:
            LOG.debug("Trying to connect to the database")

            # Create the SQLAlchemy engine.
            self.__engine = sql_server.create_engine()
            LOG.debug(self.__engine)

            self.__session = sessionmaker(bind=self.__engine)

            self.__engine.execute('SELECT 1')
            self.__db_status = sql_server.check_schema()
            self.__last_connect_attempt = None

            if self.__db_status == DBStatus.SCHEMA_MISSING and init_db:
                LOG.debug("Initializing new database schema.")
                self.__db_status = sql_server.connect(init_db)

        except Exception as ex:
            LOG.exception("The database for product '%s' cannot be"
                          " connected to.", self.endpoint)
            self.__db_status = DBStatus.FAILED_TO_CONNECT
            self.__last_connect_attempt = (datetime.now(), str(ex))

    def get_details(self):
        """
        Get details for a product from the database.

        It may throw different error messages depending on the used SQL driver
        adapter in case of connection error.
        """
        with DBSession(self.session_factory) as run_db_session:
            run_locks = run_db_session.query(RunLock.name) \
                .filter(RunLock.locked_at.isnot(None)) \
                .all()

            runs_in_progress = set(run_lock[0] for run_lock in run_locks)

            num_of_runs = run_db_session.query(Run).count()

            latest_store_to_product = ""
            if num_of_runs:
                last_updated_run = run_db_session.query(Run) \
                    .order_by(Run.date.desc()) \
                    .limit(1) \
                    .one_or_none()

                latest_store_to_product = last_updated_run.date

        return num_of_runs, runs_in_progress, latest_store_to_product

    def teardown(self):
        """
        Disposes the database connection to the product's backend.
        """
        if self.__db_status == DBStatus.FAILED_TO_CONNECT:
            return

        self.__engine.dispose()

        self.__session = None
        self.__engine = None

    def cleanup_run_db(self):
        """
        Cleanup the run database which belongs to this product.
        """
        LOG.info("[%s] Garbage collection started...", self.endpoint)

        db_cleanup.remove_expired_data(self)
        db_cleanup.remove_unused_data(self)
        db_cleanup.update_contextual_data(self, self.__context)

        LOG.info("[%s] Garbage collection finished.", self.endpoint)
        return True

    def set_cached_run_data(self,
                            config_db_session_factory,
                            number_of_runs_change: Optional[int] = None,
                            last_store_date: Optional[datetime] = None):
        """
        Update the configuration database row for the current `Product`
        for the keys that contain cached summaries of what would otherwise
        be queriable from the product's database.
        """
        updates = {}

        if number_of_runs_change:
            updates["num_of_runs"] = DBProduct.num_of_runs \
                + number_of_runs_change
            LOG.info("%s: Changing 'num_of_runs' in CONFIG database by %s%i.",
                     self.__endpoint,
                     '+' if number_of_runs_change > 0 else '-',
                     abs(number_of_runs_change))

        if last_store_date:
            updates["latest_storage_date"] = last_store_date

        if updates:
            with DBSession(config_db_session_factory) as session:
                session.query(DBProduct) \
                    .filter(DBProduct.id == self.__id) \
                    .update(updates)
                session.commit()
