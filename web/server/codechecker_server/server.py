# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Main server starts a http server which handles Thrift client
and browser requests.
"""


import atexit
import datetime
from hashlib import sha256
from multiprocessing import Process
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

from http.server import HTTPServer, BaseHTTPRequestHandler, \
    SimpleHTTPRequestHandler

from sqlalchemy.orm import sessionmaker
from thrift.protocol import TJSONProtocol
from thrift.transport import TTransport
from thrift.Thrift import TApplicationException
from thrift.Thrift import TMessageType

from codechecker_api_shared.ttypes import DBStatus
from codechecker_api.Authentication_v6 import \
    codeCheckerAuthentication as AuthAPI_v6
from codechecker_api.Configuration_v6 import \
    configurationService as ConfigAPI_v6
from codechecker_api.codeCheckerDBAccess_v6 import \
    codeCheckerDBAccess as ReportAPI_v6
from codechecker_api.ProductManagement_v6 import \
    codeCheckerProductService as ProductAPI_v6
from codechecker_api.ServerInfo_v6 import \
    serverInfoService as ServerInfoAPI_v6

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
from .api.server_info_handler import \
    ThriftServerInfoHandler as ServerInfoHandler_v6
from .database import database, db_cleanup
from .database.config_db_model import Product as ORMProduct, \
    Configuration as ORMConfiguration
from .database.database import DBSession
from .database.run_db_model import IDENTIFIER as RUN_META, Run, RunLock

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
        cookies = self.headers.get("Cookie")
        if cookies:
            split = cookies.split("; ")
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
            client_host, client_port, is_ipv6 = \
                RequestHandler._get_client_host_port(self.client_address)
            LOG.debug("%s:%s Invalid access, credentials not found - "
                      "session refused",
                      client_host if not is_ipv6 else '[' + client_host + ']',
                      str(client_port))
            return None

    def __has_access_permission(self, product):
        """
        Returns True if the currently authenticated user has access permission
        on the given product.
        """
        with DBSession(self.server.config_session) as session:
            perm_args = {'productID': product.id,
                         'config_db_session': session}
            return permissions.require_permission(
                permissions.PRODUCT_ACCESS,
                perm_args,
                self.auth_session)

    def __handle_readiness(self):
        """ Handle readiness probe. """
        try:
            cfg_sess = self.server.config_session()
            cfg_sess.query(ORMConfiguration).count()

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'CODECHECKER_SERVER_IS_READY')
        except Exception:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'CODECHECKER_SERVER_IS_NOT_READY')
        finally:
            if cfg_sess:
                cfg_sess.close()
                cfg_sess.commit()

    def __handle_liveness(self):
        """ Handle liveness probe. """
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'CODECHECKER_SERVER_IS_LIVE')

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

    @staticmethod
    def _get_client_host_port(address):
        """
        Returns the host and port of the request's address, and whether it
        was an IPv6 address.
        """
        if len(address) == 2:
            return address[0], address[1], False
        if len(address) == 4:
            return address[0], address[1], True

        raise IndexError("Invalid address tuple given.")

    def do_GET(self):
        """ Handles the SPA browser access (GET requests).

        It will do the following steps:
         - for requests for index.html ('/'), just respond with the file.
         - if the requested path contains a product endpoint name
           ('/prod/app.js', '/prod/runs'), remove the endpoint from the path.
         - if the requested path is a valid file (e.g: 'app.js'), respond with
           the file.
         - otherwise (e.g: 'runs') respond with index.html.
        """
        client_host, client_port, is_ipv6 = \
            RequestHandler._get_client_host_port(self.client_address)
        self.auth_session = self.__check_session_cookie()

        username = self.auth_session.user if self.auth_session else 'Anonymous'
        LOG.debug("%s:%s -- [%s] GET %s",
                  client_host if not is_ipv6 else '[' + client_host + ']',
                  client_port, username, self.path)

        if self.path == '/':
            self.path = 'index.html'
            SimpleHTTPRequestHandler.do_GET(self)
            return

        if self.path == '/live':
            self.__handle_liveness()
            return

        if self.path == '/ready':
            self.__handle_readiness()
            return

        product_endpoint, _ = routing.split_client_GET_request(self.path)

        # Check that path contains a product endpoint.
        if product_endpoint is not None and product_endpoint != '':
            self.path = self.path.replace(
                "{0}/".format(product_endpoint), "", 1)

        if self.path == '/':
            self.path = "index.html"

        # Check that the given path is a file.
        if not os.path.exists(self.translate_path(self.path)):
            self.path = 'index.html'

        SimpleHTTPRequestHandler.do_GET(self)

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
        protocol_factory = TJSONProtocol.TJSONProtocolFactory()
        input_protocol_factory = protocol_factory
        output_protocol_factory = protocol_factory

        # Get Thrift API function name to print to the log output.
        itrans = TTransport.TFileObjectTransport(self.rfile)
        itrans = TTransport.TBufferedTransport(itrans,
                                               int(self.headers[
                                                   'Content-Length']))
        iprot = input_protocol_factory.getProtocol(itrans)
        fname, _, _ = iprot.readMessageBegin()

        client_host, client_port, is_ipv6 = \
            RequestHandler._get_client_host_port(self.client_address)
        self.auth_session = self.__check_session_cookie()
        auth_user = \
            self.auth_session.user if self.auth_session else "Anonymous"
        host_info = client_host if not is_ipv6 else '[' + client_host + ']'
        api_info = f"{host_info}:{client_port} -- [{auth_user}] POST " \
                   f"{self.path}@{fname}"
        LOG.info(api_info)

        # Create new thrift handler.
        version = self.server.version

        cstringio_buf = itrans.cstringio_buf.getvalue()
        itrans = TTransport.TMemoryBuffer(cstringio_buf)
        iprot = input_protocol_factory.getProtocol(itrans)

        otrans = TTransport.TMemoryBuffer()
        oprot = output_protocol_factory.getProtocol(otrans)

        if self.server.manager.is_enabled and \
                not self.path.endswith(('/Authentication',
                                        '/Configuration',
                                        '/ServerInfo')) and \
                not self.auth_session:
            # Bail out if the user is not authenticated...
            # This response has the possibility of melting down Thrift clients,
            # but the user is expected to properly authenticate first.
            LOG.debug("%s:%s Invalid access, credentials not found "
                      "- session refused.",
                      client_host if not is_ipv6 else '[' + client_host + ']',
                      str(client_port))

            self.send_thrift_exception("Error code 401: Unauthorized!", iprot,
                                       oprot, otrans)
            return

        # Authentication is handled, we may now respond to the user.
        try:
            product_endpoint, api_ver, request_endpoint = \
                routing.split_client_POST_request(self.path)
            if product_endpoint is None and api_ver is None and\
                    request_endpoint is None:
                raise Exception("Invalid request endpoint path.")

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
                    elif request_endpoint == 'ServerInfo':
                        server_info_handler = ServerInfoHandler_v6(version)
                        processor = ServerInfoAPI_v6.Processor(
                            server_info_handler)
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
                            version,
                            self.server.context)
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

        except BrokenPipeError as ex:
            LOG.warning("%s failed with BrokenPipeError: %s",
                        api_info, str(ex))
            import traceback
            traceback.print_exc()
        except Exception as ex:
            LOG.warning("%s failed with Exception: %s", api_info, str(ex))
            import traceback
            traceback.print_exc()

            cstringio_buf = itrans.cstringio_buf.getvalue()
            if cstringio_buf:
                itrans = TTransport.TMemoryBuffer(cstringio_buf)
                iprot = input_protocol_factory.getProtocol(itrans)

            self.send_thrift_exception(str(ex), iprot, oprot, otrans)
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
        path = posixpath.normpath(urllib.parse.unquote(path))
        words = path.split('/')
        words = [_f for _f in words if _f]
        path = self.server.www_root
        for word in words:
            _, word = os.path.splitdrive(word)
            _, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path


class Product:
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

            runs_in_progress = set([run_lock[0] for run_lock in run_locks])

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
        LOG.info("Garbage collection for product '%s' started...",
                 self.endpoint)

        db_cleanup.remove_expired_run_locks(self.session_factory)
        db_cleanup.remove_unused_data(self.session_factory)
        db_cleanup.upgrade_severity_levels(self.session_factory,
                                           self.__context.checker_labels)

        LOG.info("Garbage collection finished.")
        return True


class CCSimpleHttpServer(HTTPServer):
    """
    Simple http server to handle requests from the clients.
    """

    daemon_threads = False
    address_family = socket.AF_INET  # IPv4

    def __init__(self,
                 server_address,
                 RequestHandlerClass,
                 config_directory,
                 product_db_sql_server,
                 skip_db_cleanup,
                 pckg_data,
                 context,
                 check_env,
                 manager):

        LOG.debug("Initializing HTTP server...")

        self.config_directory = config_directory
        self.www_root = pckg_data['www_root']
        self.doc_root = pckg_data['doc_root']
        self.version = pckg_data['version']
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

        try:
            HTTPServer.__init__(self, server_address,
                                RequestHandlerClass,
                                bind_and_activate=True)
            ssl_key_file = os.path.join(config_directory, "key.pem")
            ssl_cert_file = os.path.join(config_directory, "cert.pem")

            self.configure_keepalive()

            if os.path.isfile(ssl_key_file) and os.path.isfile(ssl_cert_file):
                LOG.info("Initiating SSL. Server listening on secure socket.")
                LOG.debug("Using cert file: %s", ssl_cert_file)
                LOG.debug("Using key file: %s", ssl_key_file)
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(certfile=ssl_cert_file,
                                            keyfile=ssl_key_file)
                # FIXME introduce with python 3.7
                # ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

                # TLS1 and TLS1.1 were deprecated in RFC8996
                # https://datatracker.ietf.org/doc/html/rfc8996
                ssl_context.options |= (ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1)
                self.socket = ssl_context.wrap_socket(self.socket,
                                                      server_side=True)

            else:
                LOG.info("Searching for SSL key at %s, cert at %s, "
                         "not found...", ssl_key_file, ssl_cert_file)
                LOG.info("Falling back to simple, insecure HTTP.")

        except Exception as e:
            LOG.error("Couldn't start the server: %s", e.__str__())
            raise

    def configure_keepalive(self):
        """
        Enable keepalive on the socket and some TCP keepalive configuration
        option based on the server configuration file.
        """
        if not self.manager.is_keepalive_enabled():
            return

        keepalive_is_on = self.socket.getsockopt(socket.SOL_SOCKET,
                                                 socket.SO_KEEPALIVE)
        if keepalive_is_on != 0:
            LOG.debug('Socket keepalive already on.')
        else:
            LOG.debug('Socket keepalive off, turning on.')

        ret = self.socket.setsockopt(socket.SOL_SOCKET,
                                     socket.SO_KEEPALIVE, 1)
        if ret:
            LOG.error('Failed to set socket keepalive: %s', ret)

        idle = self.manager.get_keepalive_idle()
        if idle:
            ret = self.socket.setsockopt(socket.IPPROTO_TCP,
                                         socket.TCP_KEEPIDLE, idle)
            if ret:
                LOG.error('Failed to set TCP keepalive idle: %s', ret)

        interval = self.manager.get_keepalive_interval()
        if interval:
            ret = self.socket.setsockopt(socket.IPPROTO_TCP,
                                         socket.TCP_KEEPINTVL, interval)
            if ret:
                LOG.error('Failed to set TCP keepalive interval: %s', ret)

        max_probe = self.manager.get_keepalive_max_probe()
        if max_probe:
            ret = self.socket.setsockopt(socket.IPPROTO_TCP,
                                         socket.TCP_KEEPCNT, max_probe)
            if ret:
                LOG.error('Failed to set TCP max keepalive probe: %s', ret)

    def terminate(self):
        """
        Terminating the server.
        """
        try:
            self.server_close()
            self.__engine.dispose()
        except Exception as ex:
            LOG.error("Failed to shut down the WEB server!")
            LOG.error(str(ex))
            sys.exit(1)

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
        [self.remove_product(ep)
            for ep in list(self.__products)
            if ep not in endpoints_to_keep]


class CCSimpleHttpServerIPv6(CCSimpleHttpServer):
    """
    CodeChecker HTTP simple server that listens over an IPv6 socket.
    """

    address_family = socket.AF_INET6

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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

    sha = sha256((username + ':' + password).encode('utf-8')).hexdigest()
    secret = f"{username}:{sha}"
    with open(root_file, 'w', encoding="utf-8", errors="ignore") as f:
        LOG.debug("Save root SHA256 '%s'", secret)
        f.write(secret)

    # This file should be only readable by the process owner, and noone else.
    os.chmod(root_file, stat.S_IRUSR)

    return secret


def start_server(config_directory, package_data, port, config_sql_server,
                 listen_address, force_auth, skip_db_cleanup,
                 context, check_env):
    """
    Start http server to handle web client and thrift requests.
    """
    LOG.debug("Starting CodeChecker server...")

    server_addr = (listen_address, port)

    root_file = os.path.join(config_directory, 'root.user')
    if not os.path.exists(root_file):
        LOG.warning("Server started without 'root.user' present in "
                    "CONFIG_DIRECTORY!")
        root_sha = __make_root_file(root_file)
    else:
        LOG.debug("Root file was found. Loading...")
        try:
            with open(root_file, 'r', encoding="utf-8", errors="ignore") as f:
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
        example_cfg_file = os.path.join(os.environ['CC_DATA_FILES_DIR'],
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

    server_clazz = CCSimpleHttpServer
    if ':' in server_addr[0]:
        # IPv6 address specified for listening.
        # FIXME: Python>=3.8 automatically handles IPv6 if ':' is in the bind
        # address, see https://bugs.python.org/issue24209.
        server_clazz = CCSimpleHttpServerIPv6

    http_server = server_clazz(server_addr,
                               RequestHandler,
                               config_directory,
                               config_sql_server,
                               skip_db_cleanup,
                               package_data,
                               context,
                               check_env,
                               manager)

    # If the server was started with the port 0, the OS will pick an available
    # port. For this reason we will update the port variable after server
    # initialization.
    port = http_server.socket.getsockname()[1]

    processes = []

    def signal_handler(signum, frame):
        """
        Handle SIGTERM to stop the server running.
        """
        LOG.info("Shutting down the WEB server on [%s:%d]",
                 '[' + listen_address + ']'
                 if server_clazz is CCSimpleHttpServerIPv6 else listen_address,
                 port)
        http_server.terminate()

        # Terminate child processes.
        for pp in processes:
            pp.terminate()

        sys.exit(128 + signum)

    def reload_signal_handler(*args, **kwargs):
        """
        Reloads server configuration file.
        """
        manager.reload_config()

    try:
        instance_manager.register(os.getpid(),
                                  os.path.abspath(
                                      context.codechecker_workspace),
                                  port)
    except IOError as ex:
        LOG.debug(ex.strerror)

    LOG.info("Server waiting for client requests on [%s:%d]",
             '[' + listen_address + ']'
             if server_clazz is CCSimpleHttpServerIPv6 else listen_address,
             port)

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

    for _ in range(manager.worker_processes - 1):
        p = Process(target=http_server.serve_forever)
        processes.append(p)
        p.start()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if sys.platform != "win32":
        signal.signal(signal.SIGHUP, reload_signal_handler)

    # Main process also acts as a worker.
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
