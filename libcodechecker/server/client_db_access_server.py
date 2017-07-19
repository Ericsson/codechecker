# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Main server starts a http server which handles Thrift client
and browser requests.
"""
import atexit
import base64
import datetime
import errno
from multiprocessing.pool import ThreadPool
import os
import posixpath
import socket
import urllib
import urlparse

try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from SimpleHTTPServer import SimpleHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler, \
        SimpleHTTPRequestHandler

from sqlalchemy.orm import sessionmaker
from thrift.protocol import TJSONProtocol
from thrift.transport import TTransport

from Authentication import codeCheckerAuthentication
from codeCheckerDBAccess import codeCheckerDBAccess
from ProductManagement import codeCheckerProductService

from libcodechecker import session_manager
from libcodechecker.logger import LoggerFactory

from . import database_handler
from . import instance_manager
from client_auth_handler import ThriftAuthHandler
from client_db_access_handler import ThriftRequestHandler
from config_db_model import Product as ORMProduct
from product_db_access_handler import ThriftProductHandler
from run_db_model import IDENTIFIER as RUN_META

LOG = LoggerFactory.get_new_logger('DB ACCESS')

# A list of top-level path elements under the webserver root
# which should not be considered as a product route.
NON_PRODUCT_NAMES = ['products.html',
                     'index.html',
                     'fonts',
                     'images',
                     'scripts',
                     'style'
                     ]

# A list of top-level path elements in requests (such as Thrift endpoints)
# which should not be considered as a product route.
NON_PRODUCT_NAMES += ['Authentication',
                      'Products',
                      'CodeCheckerService'
                      ]


class RequestHandler(SimpleHTTPRequestHandler):
    """
    Handle thrift and browser requests
    Simply modified and extended version of SimpleHTTPRequestHandler
    """

    def __init__(self, request, client_address, server):
        BaseHTTPRequestHandler.__init__(self,
                                        request,
                                        client_address,
                                        server)

    def log_message(self, msg_format, *args):
        """ Silencing http server. """
        return

    def __check_auth_in_request(self):
        """
        Wrapper to handle authentication needs from both GET and POST requests.
        Returns a session object if correct cookie is presented or creates a
        new session if the Authorization header and the correct credentials are
        present.
        """

        if not self.server.manager.isEnabled():
            return None

        success = None

        # Authentication can happen in two possible ways:
        #
        # The user either presents a valid session cookie -- in this case
        # checking if the session for the given cookie is valid.

        client_host, client_port = self.client_address

        for k in self.headers.getheaders("Cookie"):
            split = k.split("; ")
            for cookie in split:
                values = cookie.split("=")
                if len(values) == 2 and \
                        values[0] == session_manager.SESSION_COOKIE_NAME:
                    if self.server.manager.is_valid(values[1], True):
                        # The session cookie contains valid data.
                        success = self.server.manager.get_session(values[1],
                                                                  True)

        if success is None:
            # Session cookie was invalid (or not found...)
            # Attempt to see if the browser has sent us
            # an authentication request.
            authHeader = self.headers.getheader("Authorization")
            if authHeader is not None and authHeader.startswith("Basic "):
                LOG.info("Client from " + client_host + ":" +
                         str(client_port) + " attempted authorization.")
                authString = base64.decodestring(
                    self.headers.getheader("Authorization").
                    replace("Basic ", ""))

                session = self.server.manager.create_or_get_session(
                    authString)
                if session:
                    LOG.info("Client from " + client_host + ":" +
                             str(client_port) +
                             " successfully logged in as user " +
                             session.user)
                    return session

        # Else, access is still not granted.
        if success is None:
            LOG.debug(client_host + ":" + str(client_port) +
                      " Invalid access, credentials not found " +
                      "- session refused.")
            return None

        return success

    def __get_product_name(self):
        """
        Get product name from the request's URI.
        """

        # A standard request from a browser looks like:
        # http://localhost:8001/[product-name]/#{request-parts}
        # where the parts are, e.g.: run=[run_id]&report=[report_id]
        #
        # Rewrite the "product-name" so that the web-server deploys the
        # viewer client from the www/ folder.

        # The split array looks like ['', 'product-name', ...].
        first_part = urlparse.urlparse(self.path).path.split('/', 2)[1]
        return first_part if first_part not in NON_PRODUCT_NAMES else None

    def do_GET(self):
        """
        Handles the webbrowser access (GET requests).
        """

        LOG.info("{0}:{1} -- GET {2}".format(self.client_address[0],
                                             str(self.client_address[1]),
                                             self.path))

        auth_session = self.__check_auth_in_request()
        if self.server.manager.isEnabled() and not auth_session:
            realm = self.server.manager.getRealm()["realm"]
            error_body = self.server.manager.getRealm()["error"]

            self.send_response(401)  # 401 Unauthorised
            self.send_header("WWW-Authenticate",
                             'Basic realm="{0}"'.format(realm))
            self.send_header("Content-type", "text/plain")
            self.send_header("Content-length", str(len(error_body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(error_body)
            return
        else:
            product_name = self.__get_product_name()

            if product_name is not None and product_name != '':
                if not self.server.get_product(product_name):
                    LOG.info("Product named '{0}' does not exist."
                             .format(product_name))
                    self.send_error(
                        404,
                        "The product {0} does not exist.".format(product_name))
                    return

                if product_name + '/' not in self.path:
                    # /prod must be routed to /prod/index.html first, so later
                    # queries for web resources are '/prod/style...' as
                    # opposed to '/style...', which would result in "style"
                    # being considered product name.
                    LOG.debug("Redirecting user from /{0} to /{0}/index.html"
                              .format(product_name))

                    # WARN: Browsers cache '308 Permanent Redirect' responses,
                    # in the event of debugging this, use Private Browsing!
                    self.send_response(308)
                    self.send_header("Location",
                                     self.path.replace(product_name,
                                                       product_name + '/', 1))
                    self.end_headers()
                    return
                else:
                    # Serves the main page and the resources:
                    # /prod/(index.html) -> /(index.html)
                    # /prod/styles/(...) -> /styles/(...)
                    LOG.debug("Product routing before " + self.path)
                    self.path = self.path.replace(
                        "{0}/".format(product_name), "", 1)
                    LOG.debug("Product routing after: " + self.path)
            else:
                if self.path in ['/', '/index.html']:
                    only_product = self.server.get_only_product()
                    if only_product and only_product.connected:
                        LOG.debug("Redirecting '/' to ONLY product '/{0}'"
                                  .format(only_product.endpoint))

                        self.send_response(307)  # 307 Temporary Redirect
                        self.send_header("Location",
                                         '/{0}'.format(only_product.endpoint))
                        self.end_headers()
                        return

                    # Route homepage queries to serving the product list.
                    LOG.debug("Serving product list as homepage.")
                    self.path = '/products.html'
                else:
                    # The path requested does not specify a product: it is most
                    # likely a resource file.
                    LOG.debug("Serving resource '{0}'".format(self.path))

                self.send_response(200)  # 200 OK
                if auth_session is not None:
                    # Browsers get a standard cookie for session.
                    self.send_header(
                        "Set-Cookie",
                        "{0}={1}; Path=/".format(
                            session_manager.SESSION_COOKIE_NAME,
                            auth_session.token))

            SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """
        Handles POST queries, which are usually Thrift messages.
        """

        client_host, client_port = self.client_address
        LOG.info("{0}:{1} -- POST {2}".format(client_host,
                                              str(client_port),
                                              self.path))

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

        auth_session = self.__check_auth_in_request()
        if self.server.manager.isEnabled() and self.path != '/Authentication' \
                and not auth_session:
            # Bail out if the user is not authenticated...
            # This response has the possibility of melting down Thrift clients,
            # but the user is expected to properly authenticate first.

            LOG.debug(client_host + ":" + str(client_port) +
                      " Invalid access, credentials not found " +
                      "- session refused.")
            self.send_error(401)
            return

        # Authentication is handled, we may now respond to the user.
        try:
            product_name = self.__get_product_name()
            request_endpoint = self.path.replace("/{0}".format(product_name),
                                                 "", 1)

            product = None
            session_makers = {}
            if product_name:
                # The current request came through a product route, and not
                # to the main endpoint.
                product = self.server.get_product(product_name)
                if not product.connected:
                    # If the product is not connected, try reconnecting...
                    LOG.debug("Request's product '{0}' is not connected! "
                              "Attempting reconnect...".format(product_name))
                    product.connect()

                    if not product.connected:
                        # If the reconnection fails, send an error to the user.
                        self.send_error(  # 500 Internal Server Error
                            500, "Product '{0}' database connection failed!"
                                 .format(product_name))
                        return

                session_makers['run_db'] = product.session_factory

            if request_endpoint == '/Authentication':
                auth_handler = ThriftAuthHandler(self.server.manager,
                                                 auth_session)
                processor = codeCheckerAuthentication.Processor(auth_handler)
            elif request_endpoint == '/Products':
                # The product server needs its own endpoint to the
                # configuration database.
                session_makers['product_db'] = self.server.product_session

                prod_handler = ThriftProductHandler(
                    self.server,
                    session_makers['product_db'],
                    product,
                    version)
                processor = codeCheckerProductService.Processor(prod_handler)
            elif request_endpoint == '/CodeCheckerService':
                # This endpoint is a product's report_server.
                if not product:
                    self.send_error(  # 404 Not Found
                        404, "The specified product '{0}' does not exist!"
                             .format(product_name))
                    return

                acc_handler = ThriftRequestHandler(
                    session_makers['run_db'],
                    auth_session,
                    checker_md_docs,
                    checker_md_docs_map,
                    suppress_handler,
                    self.server.context.run_db_version_info,
                    version)
                processor = codeCheckerDBAccess.Processor(acc_handler)
            else:
                self.send_error(404,  # 404 Not Fount
                                "No endpoint named '{0}'.".format(self.path))
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
            import traceback
            traceback.print_exc()
            LOG.error(str(exn))
            self.send_error(404, "Request failed.")
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
        self.__orm_object = orm_object
        self.__context = context
        self.__check_env = check_env
        self.__engine = None
        self.__session = None
        self.__connected = False

        self.__last_connect_attempt = None

    @property
    def id(self):
        return self.__orm_object.id

    @property
    def endpoint(self):
        """
        Returns the accessible URL endpoint of the product.
        """
        return self.__orm_object.endpoint

    @property
    def name(self):
        """
        Returns the display name of the product.
        """
        return self.__orm_object.display_name

    @property
    def session_factory(self):
        """
        Returns the session maker on this product's database engine which
        can be used to initiate transactional connections.
        """
        return self.__session

    @property
    def connected(self):
        """
        Returns whether the product has a valid connection to the managed
        database.
        """
        return self.__connected

    @property
    def last_connection_failure(self):
        """
        Returns the reason behind the last executed connection attempt's
        failure.
        """
        return self.__last_connect_attempt[1] if self.__last_connect_attempt \
            else None

    def connect(self):
        """
        Initiates the actual connection to the database configured for the
        product.
        """
        if self.__connected:
            return

        if self.__last_connect_attempt and \
                (datetime.datetime.now() - self.__last_connect_attempt[0]). \
                total_seconds() <= Product.CONNECT_RETRY_TIMEOUT:
            return

        LOG.debug("Connecting database for product '{0}'".
                  format(self.__orm_object.endpoint))

        # We need to connect to the database and perform setting up the
        # schema.
        LOG.debug("Configuring schema and migration...")
        sql_server = database_handler.SQLServer.from_connection_string(
            self.__orm_object.connection,
            RUN_META,
            self.__context.config_migration_root,
            interactive=False,
            env=self.__check_env)

        try:
            sql_server.connect(self.__context.run_db_version_info, init=True)

            # Create the SQLAlchemy engine.
            LOG.debug("Connecting database engine")
            self.__engine = sql_server.create_engine()
            self.__session = sessionmaker(bind=self.__engine)

            self.__connected = True
            self.__last_connect_attempt = None
            LOG.debug("Database connected.")
        except Exception as ex:
            LOG.error("The database for product '{0}' cannot be connected to."
                      .format(self.__orm_object.endpoint))
            LOG.error(ex.message)
            self.__connected = False
            self.__last_connect_attempt = (datetime.datetime.now(), ex.message)

    def teardown(self):
        """
        Disposes the database connection to the product's backend.
        """
        if not self.__connected:
            return

        self.__engine.dispose()

        self.__session = None
        self.__engine = None


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
        self.product_session = sessionmaker(bind=self.__engine)

        # Load the initial list of products and create the connections.
        sess = self.product_session()
        products = sess.query(ORMProduct).all()
        for product in products:
            self.add_product(product)
        sess.close()

        self.__request_handlers = ThreadPool(processes=10)
        try:
            HTTPServer.__init__(self, server_address,
                                RequestHandlerClass,
                                bind_and_activate=True)
        except Exception as e:
            LOG.error("Couldn't start the server: " + e.__str__())
            raise

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

    def add_product(self, orm_product):
        """
        Adds a product to the list of product databases connected to
        by the server.
        """
        if orm_product.endpoint in self.__products:
            raise Exception("This product is already configured!")

        LOG.info("Setting up product '{0}'".format(orm_product.endpoint))
        conn = Product(orm_product, self.context, self.check_env)
        self.__products[conn.endpoint] = conn

        conn.connect()

    def get_product(self, endpoint):
        """
        Get the product connection object for the given endpoint, or None.
        """
        return self.__products.get(endpoint, None)

    def get_only_product(self):
        """
        Returns the Product object for the only product connected to by the
        server, or None, if there are 0 or >= 2 products managed.
        """
        return self.__products.items()[0][1] if len(self.__products) == 1 \
            else None

    def remove_product(self, endpoint):
        product = self.get_product(endpoint)
        if not product:
            raise ValueError("The product with the given endpoint '{0}' does "
                             "not exist!".format(endpoint))

        LOG.info("Disconnecting product '{0}'".format(endpoint))
        product.teardown()

        del self.__products[endpoint]


def start_server(config_directory, package_data, port, db_conn_string,
                 suppress_handler, listen_address, context, check_env):
    """
    Start http server to handle web client and thrift requests.
    """
    LOG.debug("Starting CodeChecker server...")

    LOG.debug("Using suppress file '{0}'"
              .format(suppress_handler.suppress_file))

    server_addr = (listen_address, port)

    http_server = CCSimpleHttpServer(server_addr,
                                     RequestHandler,
                                     config_directory,
                                     db_conn_string,
                                     package_data,
                                     suppress_handler,
                                     context,
                                     check_env,
                                     session_manager.SessionManager())

    try:
        instance_manager.register(os.getpid(),
                                  os.path.abspath(
                                      context.codechecker_workspace),
                                  port)
    except IOError as ex:
        LOG.debug(ex.strerror)

    LOG.info("Server waiting for client requests on [{0}:{1}]"
             .format(listen_address, str(port)))

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
    if len(products) != 0:
        raise ValueError("Called create_initial_run_database on non-empty "
                         "config database -- you shouldn't have done this!")

    LOG.debug("Adding default product to the config db...")
    product = ORMProduct('Default', product_connection, 'Default',
                         "Default product created at server start.")
    sess.add(product)
    sess.commit()
    sess.close()

    LOG.debug("Default product set up.")
