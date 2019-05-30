# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Main server starts a http server which handles Thrift client
and browser requests.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
import atexit
import datetime
import errno
from hashlib import sha256
from multiprocessing.pool import ThreadPool
import os
import posixpath
from random import sample
import shutil
import signal
import socket
import ssl
import sys
import stat
import urllib

try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from SimpleHTTPServer import SimpleHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler, \
        SimpleHTTPRequestHandler

from sqlalchemy.orm import sessionmaker
from thrift.protocol import TJSONProtocol
from thrift.transport import TTransport
from thrift.Thrift import TApplicationException
from thrift.Thrift import TMessageType

from shared.ttypes import DBStatus
from Authentication_v6 import codeCheckerAuthentication as AuthAPI_v6
from Configuration_v6 import configurationService as ConfigAPI_v6
from codeCheckerDBAccess_v6 import codeCheckerDBAccess as ReportAPI_v6
from ProductManagement_v6 import codeCheckerProductService as ProductAPI_v6

from codechecker_common.logger import get_logger

from codechecker_web.shared.version import get_version_str

from . import instance_manager
from . import permissions
from . import routing
from . import session_manager

from .tmp import get_tmp_dir_hash

from .api.authentication import ThriftAuthHandler as AuthHandler_v6
from .api.config_handler import ThriftConfigHandler as ConfigHandler_v6
from .api.product_server import ThriftProductHandler as ProductHandler_v6
from .api.report_server import ThriftRequestHandler as ReportHandler_v6
from .database import database
from .database import db_cleanup
from .database.config_db_model import Product as ORMProduct
from .database.run_db_model import IDENTIFIER as RUN_META

LOG = get_logger('server')


class RequestHandler(SimpleHTTPRequestHandler):
    """
    Handle thrift and browser requests
    Simply modified and extended version of SimpleHTTPRequestHandler
    """
    auth_session = None

    def __init__(self, request, client_address, server):
        BaseHTTPRequestHandler.__init__(self,
                                        request,
                                        client_address,
                                        server)

    def log_message(self, msg_format, *args):
        """ Silencing http server. """
        return

    def send_thrift_exception(self, error_msg, iprot, oprot, otrans):
        """
        Send an exception response to the client in a proper format which can
        be parsed by the Thrift clients expecting JSON responses.
        """
        ex = TApplicationException(TApplicationException.INTERNAL_ERROR,
                                   error_msg)
        fname, _, seqid = iprot.readMessageBegin()
        oprot.writeMessageBegin(fname, TMessageType.EXCEPTION, seqid)
        ex.write(oprot)
        oprot.writeMessageEnd()
        oprot.trans.flush()
        result = otrans.getvalue()
        self.send_response(200)
        self.send_header("content-type", "application/x-thrift")
        self.send_header("Content-Length", len(result))
        self.end_headers()
        self.wfile.write(result)

    def __check_session_cookie(self):
        """
        Check the CodeChecker privileged access cookie in the request headers.

        :returns: A session_manager._Session object if a correct, valid session
        cookie was found in the headers. None, otherwise.
        """

        if not self.server.manager.is_enabled:
            return None

        session = None
        # Check if the user has presented a privileged access cookie.
        for k in self.headers.getheaders("Cookie"):
            split = k.split("; ")
            for cookie in split:
                values = cookie.split("=")
                if len(values) == 2 and \
                        values[0] == session_manager.SESSION_COOKIE_NAME:
                    session = self.server.manager.get_session(values[1])

        if session and session.is_alive:
            # If a valid session token was found and it can still be used,
            # mark that the user's last access to the server was the
            # request that resulted in the execution of this function.
            session.revalidate()
            return session
        else:
            # If the user's access cookie is no longer usable (invalid),
            # present an error.
            client_host, client_port = self.client_address
            LOG.debug(client_host + ":" + str(client_port) +
                      " Invalid access, credentials not found " +
                      "- session refused.")
            return None

    def end_headers(self):
        # Sending the authentication cookie
        # in every response if any.
        # This will update the the session cookie
        # on the clients to the newest.
        if self.auth_session:
            token = self.auth_session.token
            if token:
                self.send_header(
                    "Set-Cookie",
                    "{0}={1}; Path=/".format(
                        session_manager.SESSION_COOKIE_NAME,
                        token))

            # Set the current user name in the header.
            user_name = self.auth_session.user
            if user_name:
                self.send_header("X-User", user_name)

        SimpleHTTPRequestHandler.end_headers(self)

    def do_GET(self):
        """
        Handles the browser access (GET requests).
        """

        self.auth_session = self.__check_session_cookie()
        LOG.debug("%s:%s -- [%s] GET %s", self.client_address[0],
                  str(self.client_address[1]),
                  self.auth_session.user if self.auth_session else 'Anonymous',
                  self.path)

        product_endpoint, path = routing.split_client_GET_request(self.path)

        if self.server.manager.is_enabled and not self.auth_session \
                and routing.is_protected_GET_entrypoint(path):
            # If necessary, prompt the user for authentication.
            returnto = '?returnto=' + urllib.quote_plus(self.path.lstrip('/'))\
                if self.path != '/' else ''

            self.send_response(307)  # 307 Temporary Redirect
            self.send_header('Location', '/login.html' + returnto)
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write('')
            return

        if product_endpoint is not None and product_endpoint != '':
            # Route the user if there is a product endpoint in the request.

            product = self.server.get_product(product_endpoint)
            if not product:
                # Give an error if the user tries to access an invalid product.
                LOG.info("Product endpoint '%s' does not exist.",
                         product_endpoint)
                self.send_error(
                    404,
                    "The product {0} does not exist."
                    .format(product_endpoint))
                return

            if product:
                # Try to reconnect in these cases.
                # Do not try to reconnect if there is a schema mismatch.
                reconnect_cases = [DBStatus.FAILED_TO_CONNECT,
                                   DBStatus.MISSING,
                                   DBStatus.SCHEMA_INIT_ERROR]
                # If the product is not connected, try reconnecting...
                if product.db_status in reconnect_cases:
                    LOG.error("Request's product '%s' is not connected! "
                              "Attempting reconnect...", product_endpoint)
                    product.connect()
                    if product.db_status != DBStatus.OK:
                        # If the reconnection fails,
                        # redirect user to the products page.
                        self.send_response(307)  # 307 Temporary Redirect
                        self.send_header("Location", '/products.html')
                        self.end_headers()
                        return

            if path == '' and not self.path.endswith('/'):
                # /prod must be routed to /prod/index.html first, so later
                # queries for web resources are '/prod/style...' as
                # opposed to '/style...', which would result in 'style'
                # being considered product name.
                LOG.info("Redirecting user from /%s to /%s/index.html",
                         product_endpoint, product_endpoint)

                # WARN: Browsers cache '308 Permanent Redirect' responses,
                # in the event of debugging this, use Private Browsing!
                self.send_response(308)
                self.send_header("Location",
                                 self.path.replace(product_endpoint,
                                                   product_endpoint + '/',
                                                   1))
                self.end_headers()
                return

            # In other cases when '/prod/' is already in the request,
            # serve the main page and the resources, for example:
            # /prod/(index.html) -> /(index.html)
            # /prod/styles/(...) -> /styles/(...)
            self.path = self.path.replace(
                "{0}/".format(product_endpoint), "", 1)
        else:
            # No product endpoint in the request.

            if self.path in ['/', '/index.html']:
                # In case the homepage is requested and only one product
                # exists, try to skip the product list and redirect the user
                # to the runs immediately.
                only_product = self.server.get_only_product()
                if only_product:
                    if only_product.db_status == DBStatus.OK:
                        LOG.info("Redirecting '/' to ONLY product '/%s'",
                                 only_product.endpoint)

                        self.send_response(307)  # 307 Temporary Redirect
                        self.send_header("Location",
                                         '/{0}'.format(only_product.endpoint))
                        self.end_headers()
                        return
                    else:
                        LOG.error("ONLY product '/%s' has database issues...",
                                  only_product.endpoint)

                        self.send_response(307)  # 307 Temporary Redirect
                        self.send_header("Location", '/products.html')
                        self.end_headers()
                        return

                # If multiple products exist, route homepage queries to
                # serve the product list.
                LOG.debug("Serving product list as homepage.")
                self.path = '/products.html'

            self.send_response(200)  # 200 OK

        SimpleHTTPRequestHandler.do_GET(self)  # Actual serving of file.

    def __check_prod_db(self, product_endpoint):
        """
        Check the product database status.
        Try to reconnect in some cases.

        Returns if everything is ok with the database or throw an exception
        with the error message if something is wrong with the database.
        """

        product = self.server.get_product(product_endpoint)
        if not product:
            raise ValueError(
                "The product with the given endpoint '{0}' does "
                "not exist!".format(product_endpoint))

        if product.db_status == DBStatus.OK:
            # No reconnect needed.
            return product

        # Try to reconnect in these cases.
        # Do not try to reconnect if there is a schema mismatch.
        # If the product is not connected, try reconnecting...
        if product.db_status in [DBStatus.FAILED_TO_CONNECT,
                                 DBStatus.MISSING,
                                 DBStatus.SCHEMA_INIT_ERROR]:
            LOG.error("Request's product '%s' is not connected! "
                      "Attempting reconnect...", product.endpoint)
            product.connect()
            if product.db_status != DBStatus.OK:
                # If the reconnection fails send an error to the user.
                LOG.debug("Product reconnection failed.")
                error_msg = "'{0}' database connection " \
                    "failed!".format(product.endpoint)
                LOG.error(error_msg)
                raise ValueError(error_msg)
        else:
            # Send an error to the user.
            db_stat = DBStatus._VALUES_TO_NAMES.get(product.db_status)
            error_msg = "'{0}' database connection " \
                "failed. DB status: {1}".format(product.endpoint,
                                                str(db_stat))
            LOG.error(error_msg)
            raise ValueError(error_msg)

        return product

    def do_POST(self):
        """
        Handles POST queries, which are usually Thrift messages.
        """

        client_host, client_port = self.client_address
        self.auth_session = self.__check_session_cookie()
        LOG.info("%s:%s -- [%s] POST %s", client_host, str(client_port),
                 self.auth_session.user if self.auth_session else "Anonymous",
                 self.path)

        # Create new thrift handler.
        checker_md_docs = self.server.checker_md_docs
        checker_md_docs_map = self.server.checker_md_docs_map
        suppress_handler = self.server.suppress_handler
        version = self.server.version

        protocol_factory = TJSONProtocol.TJSONProtocolFactory()
        input_protocol_factory = protocol_factory
        output_protocol_factory = protocol_factory

        itrans = TTransport.TFileObjectTransport(self.rfile)
        itrans = TTransport.TBufferedTransport(itrans,
                                               int(self.headers[
                                                   'Content-Length']))
        otrans = TTransport.TMemoryBuffer()

        iprot = input_protocol_factory.getProtocol(itrans)
        oprot = output_protocol_factory.getProtocol(otrans)

        if self.server.manager.is_enabled and \
                not self.path.endswith(('/Authentication',
                                        '/Configuration')) and \
                not self.auth_session:
            # Bail out if the user is not authenticated...
            # This response has the possibility of melting down Thrift clients,
            # but the user is expected to properly authenticate first.
            LOG.debug("%s:%s Invalid access, credentials not found "
                      "- session refused.", client_host, str(client_port))
            self.send_error(401)
            return

        # Authentication is handled, we may now respond to the user.
        try:
            product_endpoint, api_ver, request_endpoint = \
                routing.split_client_POST_request(self.path)

            product = None
            if product_endpoint:
                # The current request came through a product route, and not
                # to the main endpoint.
                product = self.__check_prod_db(product_endpoint)

            version_supported = routing.is_supported_version(api_ver)
            if version_supported:
                major_version, _ = version_supported

                if major_version == 6:
                    if request_endpoint == 'Authentication':
                        auth_handler = AuthHandler_v6(
                            self.server.manager,
                            self.auth_session,
                            self.server.config_session)
                        processor = AuthAPI_v6.Processor(auth_handler)
                    elif request_endpoint == 'Configuration':
                        conf_handler = ConfigHandler_v6(
                            self.auth_session,
                            self.server.config_session)
                        processor = ConfigAPI_v6.Processor(conf_handler)
                    elif request_endpoint == 'Products':
                        prod_handler = ProductHandler_v6(
                            self.server,
                            self.auth_session,
                            self.server.config_session,
                            product,
                            version)
                        processor = ProductAPI_v6.Processor(prod_handler)
                    elif request_endpoint == 'CodeCheckerService':
                        # This endpoint is a product's report_server.
                        if not product:
                            error_msg = "Requested CodeCheckerService on a " \
                                         "nonexistent product: '{0}'." \
                                        .format(product_endpoint)
                            LOG.error(error_msg)
                            raise ValueError(error_msg)

                        if product_endpoint:
                            # The current request came through a
                            # product route, and not to the main endpoint.
                            product = self.__check_prod_db(product_endpoint)

                        acc_handler = ReportHandler_v6(
                            self.server.manager,
                            product.session_factory,
                            product,
                            self.auth_session,
                            self.server.config_session,
                            checker_md_docs,
                            checker_md_docs_map,
                            suppress_handler,
                            version)
                        processor = ReportAPI_v6.Processor(acc_handler)
                    else:
                        LOG.debug("This API endpoint does not exist.")
                        error_msg = "No API endpoint named '{0}'." \
                                    .format(self.path)
                        raise ValueError(error_msg)

            else:
                error_msg = "The API version you are using is not supported " \
                            "by this server (server API version: {0})!".format(
                                get_version_str())
                self.send_thrift_exception(error_msg, iprot, oprot, otrans)
                return

            processor.process(iprot, oprot)
            result = otrans.getvalue()

            self.send_response(200)
            self.send_header("content-type", "application/x-thrift")
            self.send_header("Content-Length", len(result))
            self.end_headers()
            self.wfile.write(result)
            return

        except Exception as exn:
            LOG.warning(str(exn))
            import traceback
            traceback.print_exc()
            self.send_thrift_exception(str(exn), iprot, oprot, otrans)
            return

    def list_directory(self, path):
        """ Disable directory listing. """
        self.send_error(405, "No permission to list directory")
        return None

    def translate_path(self, path):
        """
        Modified version from SimpleHTTPRequestHandler.
        Path is set to www_root.
        """
        # Abandon query parameters.
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = self.server.www_root
        for word in words:
            _, word = os.path.splitdrive(word)
            _, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path


class Product(object):
    """
    Represents a product, which is a distinct storage of analysis reports in
    a separate database (and database connection) with its own access control.
    """

    # The amount of SECONDS that need to pass after the last unsuccessful
    # connect() call so the next could be made.
    CONNECT_RETRY_TIMEOUT = 300

    def __init__(self, orm_object, context, check_env):
        """
        Set up a new managed product object for the configuration given.
        """
        self.__id = orm_object.id
        self.__endpoint = orm_object.endpoint
        self.__connection_string = orm_object.connection
        self.__display_name = orm_object.display_name
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
            self.__last_connect_attempt = (datetime.datetime.now(), str(ex))

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
        connection_str = self.__connection_string
        prod_db = \
            database.SQLServer.from_connection_string(connection_str,
                                                      RUN_META,
                                                      None,
                                                      interactive=False,
                                                      env=self.__check_env)
        with database.DBContext(prod_db) as db:
            try:
                LOG.info("Garbage collection for product '%s' started...",
                         self.endpoint)
                db_cleanup.remove_expired_run_locks(db.session)
                db_cleanup.remove_unused_files(db.session)
                db_cleanup.upgrade_severity_levels(db.session,
                                                   self.__context.severity_map)
                db.session.commit()
                LOG.info("Garbage collection finished.")
                return True
            except Exception as ex:
                db.session.rollback()
                LOG.error("Database cleanup failed.")
                LOG.error(ex)
                return False


class CCSimpleHttpServer(HTTPServer):
    """
    Simple http server to handle requests from the clients.
    """

    daemon_threads = False

    def __init__(self,
                 server_address,
                 RequestHandlerClass,
                 config_directory,
                 product_db_sql_server,
                 skip_db_cleanup,
                 pckg_data,
                 suppress_handler,
                 context,
                 check_env,
                 manager):

        LOG.debug("Initializing HTTP server...")

        self.config_directory = config_directory
        self.www_root = pckg_data['www_root']
        self.doc_root = pckg_data['doc_root']
        self.checker_md_docs = pckg_data['checker_md_docs']
        self.checker_md_docs_map = pckg_data['checker_md_docs_map']
        self.version = pckg_data['version']
        self.suppress_handler = suppress_handler
        self.context = context
        self.check_env = check_env
        self.manager = manager
        self.__products = {}

        # Create a database engine for the configuration database.
        LOG.debug("Creating database engine for CONFIG DATABASE...")
        self.__engine = product_db_sql_server.create_engine()
        self.config_session = sessionmaker(bind=self.__engine)
        self.manager.set_database_connection(self.config_session)

        # Load the initial list of products and set up the server.
        cfg_sess = self.config_session()
        permissions.initialise_defaults('SYSTEM', {
            'config_db_session': cfg_sess
        })
        products = cfg_sess.query(ORMProduct).all()
        for product in products:
            self.add_product(product)
            permissions.initialise_defaults('PRODUCT', {
                'config_db_session': cfg_sess,
                'productID': product.id
            })
        cfg_sess.commit()
        cfg_sess.close()

        if not skip_db_cleanup:
            for endpoint, product in self.__products.items():
                if not product.cleanup_run_db():
                    LOG.warning("Cleaning database for %s Failed.", endpoint)

        self.__request_handlers = ThreadPool(processes=10)
        try:
            HTTPServer.__init__(self, server_address,
                                RequestHandlerClass,
                                bind_and_activate=True)
            ssl_key_file = os.path.join(config_directory, "key.pem")
            ssl_cert_file = os.path.join(config_directory, "cert.pem")
            if os.path.isfile(ssl_key_file) and os.path.isfile(ssl_cert_file):
                LOG.info("Initiating SSL. Server listening on secure socket.")
                LOG.debug("Using cert file: %s", ssl_cert_file)
                LOG.debug("Using key file: %s", ssl_key_file)
                self.socket = ssl.wrap_socket(self.socket, server_side=True,
                                              keyfile=ssl_key_file,
                                              certfile=ssl_cert_file)

            else:
                LOG.info("Searching for SSL key at %s, cert at %s, "
                         "not found...", ssl_key_file, ssl_cert_file)
                LOG.info("Falling back to simple, insecure HTTP.")

        except Exception as e:
            LOG.error("Couldn't start the server: %s", e.__str__())
            raise

    def terminate(self):
        """
        Terminating the server.
        """
        try:
            LOG.info("Shutting down...")
            self.server_close()
            self.__engine.dispose()

            self.__request_handlers.terminate()
            self.__request_handlers.join()
        except Exception as ex:
            LOG.error("Failed to shut down the WEB server!")
            LOG.error(str(ex))
            sys.exit(1)

    def process_request_thread(self, request, client_address):
        try:
            # Finish_request instantiates request handler class.
            self.finish_request(request, client_address)
            self.shutdown_request(request)
        except socket.error as serr:
            if serr[0] == errno.EPIPE:
                LOG.debug("Broken pipe")
                LOG.debug(serr)
                self.shutdown_request(request)

        except Exception as ex:
            LOG.debug(ex)
            self.handle_error(request, client_address)
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        self.__request_handlers.apply_async(self.process_request_thread,
                                            (request, client_address))

    def add_product(self, orm_product, init_db=False):
        """
        Adds a product to the list of product databases connected to
        by the server.
        Checks the database connection for the product databases.
        """
        if orm_product.endpoint in self.__products:
            LOG.debug("This product is already configured!")
            return

        LOG.debug("Setting up product '%s'", orm_product.endpoint)

        prod = Product(orm_product,
                       self.context,
                       self.check_env)

        # Update the product database status.
        prod.connect()
        if prod.db_status == DBStatus.SCHEMA_MISSING and init_db:
            LOG.debug("Schema was missing in the database. Initializing new")
            prod.connect(init_db=True)

        self.__products[prod.endpoint] = prod

    @property
    def num_products(self):
        """
        Returns the number of products currently mounted by the server.
        """
        return len(self.__products)

    def get_product(self, endpoint):
        """
        Get the product connection object for the given endpoint, or None.
        """
        if endpoint in self.__products:
            return self.__products.get(endpoint)

        LOG.debug("Product with the given endpoint '%s' does not exist in "
                  "the local cache. Try to get it from the database.",
                  endpoint)

        # If the product doesn't find in the cache, try to get it from the
        # database.
        try:
            cfg_sess = self.config_session()
            product = cfg_sess.query(ORMProduct) \
                .filter(ORMProduct.endpoint == endpoint) \
                .limit(1).one_or_none()

            if not product:
                return None

            self.add_product(product)
            permissions.initialise_defaults('PRODUCT', {
                'config_db_session': cfg_sess,
                'productID': product.id
            })

            return self.__products.get(endpoint, None)
        finally:
            if cfg_sess:
                cfg_sess.close()
                cfg_sess.commit()

    def get_only_product(self):
        """
        Returns the Product object for the only product connected to by the
        server, or None, if there are 0 or >= 2 products managed.
        """
        return list(self.__products.items())[0][1] if self.num_products == 1 \
            else None

    def remove_product(self, endpoint):
        product = self.get_product(endpoint)
        if not product:
            raise ValueError("The product with the given endpoint '{0}' does "
                             "not exist!".format(endpoint))

        LOG.info("Disconnecting product '%s'", endpoint)
        product.teardown()

        del self.__products[endpoint]

    def remove_products_except(self, endpoints_to_keep):
        """
        Removes EVERY product connection from the server except those
        endpoints specified in :endpoints_to_keep.
        """
        map(self.remove_product, [ep for ep in self.__products.keys()
                                  if ep not in endpoints_to_keep])


def __make_root_file(root_file):
    """
    Generate a root username and password SHA. This hash is saved to the
    given file path, and is also returned.
    """

    LOG.debug("Generating initial superuser (root) credentials...")

    username = ''.join(sample("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 6))
    password = get_tmp_dir_hash()[:8]

    LOG.info("A NEW superuser credential was generated for the server. "
             "This information IS SAVED, thus subsequent server starts "
             "WILL use these credentials. You WILL NOT get to see "
             "the credentials again, so MAKE SURE YOU REMEMBER THIS "
             "LOGIN!")

    # Highlight the message a bit more, as the server owner configuring the
    # server must know this root access initially.
    credential_msg = "The superuser's username is '{0}' with the " \
                     "password '{1}'".format(username, password)
    LOG.info("-" * len(credential_msg))
    LOG.info(credential_msg)
    LOG.info("-" * len(credential_msg))

    sha = sha256(username + ':' + password).hexdigest()
    with open(root_file, 'w') as f:
        LOG.debug("Save root SHA256 '%s'", sha)
        f.write(sha)

    # This file should be only readable by the process owner, and noone else.
    os.chmod(root_file, stat.S_IRUSR)

    return sha


def start_server(config_directory, package_data, port, config_sql_server,
                 suppress_handler, listen_address, force_auth, skip_db_cleanup,
                 context, check_env):
    """
    Start http server to handle web client and thrift requests.
    """
    LOG.debug("Starting CodeChecker server...")

    LOG.debug("Using suppress file '%s'", suppress_handler.suppress_file)

    server_addr = (listen_address, port)

    root_file = os.path.join(config_directory, 'root.user')
    if not os.path.exists(root_file):
        LOG.warning("Server started without 'root.user' present in "
                    "CONFIG_DIRECTORY!")
        root_sha = __make_root_file(root_file)
    else:
        LOG.debug("Root file was found. Loading...")
        try:
            with open(root_file, 'r') as f:
                root_sha = f.read()
            LOG.debug("Root digest is '%s'", root_sha)
        except IOError:
            LOG.info("Cannot open root file '%s' even though it exists",
                     root_file)
            root_sha = __make_root_file(root_file)

    # Check whether configuration file exists, create an example if not.
    server_cfg_file = os.path.join(config_directory, 'server_config.json')
    if not os.path.exists(server_cfg_file):
        # For backward compatibility reason if the session_config.json file
        # exists we rename it to server_config.json.
        session_cfg_file = os.path.join(config_directory,
                                        'session_config.json')
        example_cfg_file = os.path.join(os.environ['CC_PACKAGE_ROOT'],
                                        'config', 'server_config.json')
        if os.path.exists(session_cfg_file):
            LOG.info("Renaming '%s' to '%s'. Please check the example "
                     "configuration file ('%s') or the user guide for more "
                     "information.", session_cfg_file,
                     server_cfg_file, example_cfg_file)
            os.rename(session_cfg_file, server_cfg_file)
        else:
            LOG.info("CodeChecker server's example configuration file "
                     "created at '%s'", server_cfg_file)
            shutil.copyfile(example_cfg_file, server_cfg_file)

    try:
        manager = session_manager.SessionManager(
            server_cfg_file,
            config_sql_server.get_connection_string(),
            root_sha,
            force_auth)
    except IOError as ioerr:
        LOG.debug(ioerr)
        LOG.error("The server's configuration file "
                  "is missing or can not be read!")
        sys.exit(1)
    except ValueError as verr:
        LOG.debug(verr)
        LOG.error("The server's configuration file is invalid!")
        sys.exit(1)

    http_server = CCSimpleHttpServer(server_addr,
                                     RequestHandler,
                                     config_directory,
                                     config_sql_server,
                                     skip_db_cleanup,
                                     package_data,
                                     suppress_handler,
                                     context,
                                     check_env,
                                     manager)

    def signal_handler(*args, **kwargs):
        """
        Handle SIGTERM to stop the server running.
        """
        LOG.info("Received shutdown request.")
        http_server.terminate()
        LOG.info("WEB server is shut down.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    def reload_signal_handler(*args, **kwargs):
        """
        Reloads server configuration file.
        """
        manager.reload_config()

    signal.signal(signal.SIGHUP, reload_signal_handler)

    try:
        instance_manager.register(os.getpid(),
                                  os.path.abspath(
                                      context.codechecker_workspace),
                                  port)
    except IOError as ex:
        LOG.debug(ex.strerror)

    LOG.info("Server waiting for client requests on [%s:%d]",
             listen_address, port)

    def unregister_handler(pid):
        """
        Handle errors during instance unregistration.
        The workspace might be removed so updating the
        config content might fail.
        """
        try:
            instance_manager.unregister(pid)
        except IOError as ex:
            LOG.debug(ex.strerror)

    atexit.register(unregister_handler, os.getpid())
    http_server.serve_forever()
    LOG.info("Webserver quit.")


def add_initial_run_database(config_sql_server, product_connection):
    """
    Create a default run database as SQLite in the config directory,
    and add it to the list of products in the config database specified by
    db_conn_string.
    """

    # Connect to the configuration database
    LOG.debug("Creating database engine for CONFIG DATABASE...")
    __engine = config_sql_server.create_engine()
    product_session = sessionmaker(bind=__engine)

    # Load the initial list of products and create the connections.
    sess = product_session()
    products = sess.query(ORMProduct).all()
    if products:
        raise ValueError("Called create_initial_run_database on non-empty "
                         "config database -- you shouldn't have done this!")

    LOG.debug("Adding default product to the config db...")
    product = ORMProduct('Default', product_connection, 'Default',
                         "Default product created at server start.")
    sess.add(product)
    sess.commit()
    sess.close()

    LOG.debug("Default product set up.")
