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
from collections import Counter
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import pathlib
import shutil
import signal
import socket
import ssl
import sys
import time
from typing import Dict, List, Optional, Tuple, cast

from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import make_url
from sqlalchemy.sql.expression import func
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
from codechecker_api.codeCheckerServersideTasks_v6 import \
    codeCheckerServersideTaskService as TaskAPI_v6

from codechecker_common import util
from codechecker_common.compatibility.multiprocessing import \
    Pool, Process, Queue, Value, cpu_count, SyncManager
from codechecker_common.logger import get_logger, signal_log

from codechecker_web.shared import database_status
from codechecker_web.shared.version import get_version_str

from . import instance_manager, permissions, routing, session_manager
from .api.authentication import ThriftAuthHandler as AuthHandler_v6
from .api.config_handler import ThriftConfigHandler as ConfigHandler_v6
from .api.product_server import ThriftProductHandler as ProductHandler_v6
from .api.report_server import ThriftRequestHandler as ReportHandler_v6
from .api.server_info_handler import \
    ThriftServerInfoHandler as ServerInfoHandler_v6
from .api.tasks import ThriftTaskHandler as TaskHandler_v6
from .database.config_db_model import Product as ORMProduct, \
    Configuration as ORMConfiguration
from .database.database import DBSession
from .database.run_db_model import Run
from .product import Product
from .task_executors.main import executor as background_task_executor
from .task_executors.task_manager import \
    TaskManager as BackgroundTaskManager


LOG = get_logger('server')


class ProductNotFoundError(ValueError):
    pass


class RequestHandler(SimpleHTTPRequestHandler):
    """
    Handle thrift and browser requests
    Simply modified and extended version of SimpleHTTPRequestHandler
    """
    auth_session = None

    def __init__(self, request, client_address, server):
        self.path = None
        super().__init__(request, client_address, server)

    def log_message(self, *_args):
        """Silencing HTTP server."""
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
        self.send_header("Content-Length", str(len(result)))
        self.end_headers()
        self.wfile.write(result)

    def __check_session_header(self):
        """
        Check the CodeChecker privileged access cookie in the request headers.

        :returns: A session_manager._Session object if a correct, valid session
        cookie was found in the headers. None, otherwise.
        """

        if not self.server.manager.is_enabled:
            return None

        session = None
        # Check if the user has presented a bearer token for authentication.
        token = self.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token.split("Bearer ", 1)[1]
            session = self.server.manager.get_session(token)

        # Check if the user has presented a privileged access cookie.
        # This method is used by older command-line clients, and since cookies
        # with an expiration date were purged when updating, the web interface
        # should no longer have a valid access token as a cookie.
        # DEPRECATED: Will be removed in a future version.
        cookies = self.headers.get("Cookie")
        if not session and cookies:
            split = cookies.split("; ")
            for cookie in split:
                values = cookie.split("=")
                if len(values) == 2 and \
                        values[0] == session_manager.SESSION_COOKIE_NAME:
                    session = self.server.manager.get_session(values[1])

        if session and session.is_alive:
            # If a valid bearer token was found and it can still be used,
            # mark that the user's last access to the server was the
            # request that resulted in the execution of this function.
            session.revalidate()
            return session
        else:
            # If the user's token is no longer usable (invalid),
            # present an error.
            client_host, client_port, is_ipv6 = \
                RequestHandler._get_client_host_port(self.client_address)
            LOG.debug(
                "%s:%s Invalid access, credentials not found - "
                "session refused",
                client_host if not is_ipv6 else '[' + client_host + ']',
                str(client_port))
            return None

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
        """
        Headers in this section are based on the OWASP Secure Headers Project.
        https://owasp.org/www-project-secure-headers/
        They are adapted to not allow any cross-site requests.
        """
        if self.command in ['GET', 'HEAD', 'POST']:
            csp_header = 'default-src \'self\'; ' + \
                         'style-src \'unsafe-inline\' \'self\'; ' + \
                         'script-src \'unsafe-inline\' \'self\'; ' + \
                         'form-action \'self\'; ' + \
                         'frame-ancestors \'none\''
            if self.server.ssl_enabled:
                csp_header = csp_header + '; ' + \
                             'upgrade-insecure-requests; ' + \
                             'block-all-mixed-content'

            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('X-XSS-Protection', '1; mode=block')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', csp_header)
            self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
            self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            self.send_header('Referrer-Policy', 'no-referrer')

        if self.auth_session:
            # Set the current user name in the header.
            user_name = self.auth_session.user
            if user_name:
                self.send_header("X-User", user_name)

        # If the user has a leftover session cookie, try removing it.
        # Command-line clients ignore overwriting the cookie, but web clients
        # will remove the cookie from the browser.
        # DEPRECATED: Will be removed in a future version.
        # Note that if a request fails early in the process (eg. with a
        # bad HTTP header), the headers attribute might not exist yet.
        elif hasattr(self, 'headers') and self.headers.get('Cookie'):
            self.send_header('Set-Cookie',
                             session_manager.SESSION_COOKIE_NAME + '=; ' +
                             'Path=/; ' +
                             'Max-Age=0; ' +
                             'HttpOnly; ' +
                             'SameSite=Strict')

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

    def do_OPTIONS(self):  # pylint: disable=C0103
        """
        Handle OPTIONS requests.

        Always returns 403 to indicate that no cross-site requests are allowed.
        No CORS heeaders are allowed next to the 403 response.
        """
        client_host, client_port, is_ipv6 = \
            RequestHandler._get_client_host_port(self.client_address)

        LOG.debug("%s:%s -- [Anonymous] OPTIONS %s",
                  client_host if not is_ipv6 else '[' + client_host + ']',
                  client_port, self.path)

        self.send_response(403)
        self.end_headers()

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

        # GET requests are served from www_root.
        self.directory = self.server.www_root

        # Bearer tokens are not sent alongside GET requests.
        LOG.debug("%s:%s -- [Anonymous] GET %s",
                  client_host if not is_ipv6 else '[' + client_host + ']',
                  client_port, self.path)

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
            self.path = self.path.replace(f"{product_endpoint}/", "", 1)
            # Remove extra leading slashes, see cpython#93789.
            self.path = '/' + self.path.lstrip('/')

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
            raise ProductNotFoundError(
                f"The product with the given endpoint '{product_endpoint}' "
                "does not exist!")

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
                error_msg = f"'{product.endpoint}' database connection failed!"
                LOG.error(error_msg)
                raise ValueError(error_msg)
        else:
            # Send an error to the user.
            db_stat = DBStatus._VALUES_TO_NAMES.get(product.db_status)
            error_msg = f"'{product.endpoint}' database connection " \
                f"failed. DB status: {str(db_stat)}"
            LOG.error(error_msg)
            raise ValueError(error_msg)

        return product

    # pylint: disable=invalid-name
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
        self.auth_session = self.__check_session_header()
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

        product_endpoint, api_ver, request_endpoint = \
            routing.split_client_POST_request(self.path)

        if product_endpoint is None and api_ver is None and \
                request_endpoint is None:
            self.send_thrift_exception("Invalid request endpoint path.", iprot,
                                       oprot, otrans)
            return

        # Only Authentication, Configuration, ServerInof
        # endpoints are allowed for Anonymous users
        # if authentication is required.
        if self.server.manager.is_enabled and \
                request_endpoint not in \
                ['Authentication', 'Configuration', 'ServerInfo'] and \
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
            product = None
            if product_endpoint:
                # The current request came through a product route, and not
                # to the main endpoint.
                product = self.__check_prod_db(product_endpoint)

            version_supported = routing.is_supported_version(api_ver)
            if version_supported:
                major_version, _ = version_supported

                if major_version == 6:
                    if request_endpoint == "Authentication":
                        auth_handler = AuthHandler_v6(
                            self.server.manager,
                            self.auth_session,
                            self.server.config_session)
                        processor = AuthAPI_v6.Processor(auth_handler)
                    elif request_endpoint == "Configuration":
                        conf_handler = ConfigHandler_v6(
                            self.auth_session,
                            self.server.config_session,
                            self.server.manager)
                        processor = ConfigAPI_v6.Processor(conf_handler)
                    elif request_endpoint == "ServerInfo":
                        server_info_handler = ServerInfoHandler_v6(version)
                        processor = ServerInfoAPI_v6.Processor(
                            server_info_handler)
                    elif request_endpoint == "Products":
                        prod_handler = ProductHandler_v6(
                            self.server,
                            self.auth_session,
                            self.server.config_session,
                            product,
                            version)
                        processor = ProductAPI_v6.Processor(prod_handler)
                    elif request_endpoint == "Tasks":
                        task_handler = TaskHandler_v6(
                            self.server.config_session,
                            self.server.task_manager,
                            self.auth_session)
                        processor = TaskAPI_v6.Processor(task_handler)
                    elif request_endpoint == "CodeCheckerService":
                        # This endpoint is a product's report_server.
                        if not product:
                            error_msg = \
                                "Requested CodeCheckerService on a " \
                                f"nonexistent product: '{product_endpoint}'."
                            LOG.error(error_msg)
                            raise ValueError(error_msg)

                        if product_endpoint:
                            # The current request came through a
                            # product route, and not to the main endpoint.
                            product = self.__check_prod_db(product_endpoint)

                        acc_handler = ReportHandler_v6(
                            self.server.manager,
                            self.server.task_manager,
                            product.session_factory,
                            product,
                            self.auth_session,
                            self.server.config_session,
                            version,
                            api_ver,
                            self.server.context)
                        processor = ReportAPI_v6.Processor(acc_handler)
                    else:
                        LOG.debug("This API endpoint does not exist.")
                        error_msg = f"No API endpoint named '{self.path}'."
                        raise ValueError(error_msg)
                else:
                    raise ValueError(
                        f"API version {major_version} not supported")

            else:
                error_msg = \
                    "The API version you are using is not supported " \
                    "by this server (server API version: " \
                    f"{get_version_str()})!"
                self.send_thrift_exception(error_msg, iprot, oprot, otrans)
                return

            processor.process(iprot, oprot)
            result = otrans.getvalue()

            self.send_response(200)
            self.send_header("content-type", "application/x-thrift")
            self.send_header("Content-Length", str(len(result)))
            self.end_headers()
            self.wfile.write(result)
            return

        except BrokenPipeError as ex:
            LOG.warning("%s failed with BrokenPipeError: %s",
                        api_info, str(ex))
            import traceback
            traceback.print_exc()
        except Exception as ex:
            if isinstance(ex, ProductNotFoundError):
                LOG.debug("%s failed with Exception: %s", api_info, str(ex))
            else:
                LOG.warning("%s failed with Exception: %s", api_info, str(ex))
                import traceback
                traceback.print_exc()

            cstringio_buf = itrans.cstringio_buf.getvalue()
            if cstringio_buf:
                itrans = TTransport.TMemoryBuffer(cstringio_buf)
                iprot = input_protocol_factory.getProtocol(itrans)

            self.send_thrift_exception(str(ex), iprot, oprot, otrans)

    def list_directory(self, path):
        """ Disable directory listing. """
        self.send_error(405, "No permission to list directory")


def _do_db_cleanup(context, check_env,
                   id_: int, endpoint: str, display_name: str,
                   connection_str: str) -> Tuple[Optional[bool], str]:
    # This functions is a concurrent job handler!
    try:
        prod = Product(id_, endpoint, display_name, connection_str,
                       context, check_env)
        prod.connect(init_db=False)
        if prod.db_status != DBStatus.OK:
            status_str = database_status.db_status_msg.get(prod.db_status)
            return None, \
                f"Cleanup not attempted, database status is \"{status_str}\""

        prod.cleanup_run_db()
        prod.teardown()

        # Result is hard-wired to True, because the db_cleanup routines
        # swallow and log the potential errors but do not return them.
        return True, ""
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, str(e)


def _do_db_cleanups(config_database, context, check_env) \
        -> Tuple[bool, List[Tuple[str, str]]]:
    """
    Performs on-demand start-up database cleanup on all the products present
    in the ``config_database``.

    Returns whether database clean-up succeeded for all products, and the
    list of products for which it failed, along with the failure reason.
    """
    def _get_products() -> List[Product]:
        products = []
        cfg_engine = config_database.create_engine()
        cfg_session_factory = sessionmaker(bind=cfg_engine)
        with DBSession(cfg_session_factory) as cfg_db:
            for row in cfg_db.query(ORMProduct) \
                    .order_by(ORMProduct.endpoint.asc()) \
                    .all():
                products.append((row.id, row.endpoint, row.display_name,
                                 row.connection))
        cfg_engine.dispose()
        return products

    products = _get_products()
    if not products:
        return True, []

    thr_count = util.clamp(1, len(products), cpu_count())
    overall_result, failures = True, []
    with Pool(max_workers=thr_count) as executor:
        LOG.info("Performing database cleanup using %d concurrent jobs...",
                 thr_count)
        for product, result in \
                zip(products, executor.map(
                    partial(_do_db_cleanup, context, check_env),
                    *zip(*products))):
            success, reason = result
            if not success:
                _, endpoint, _, _ = product
                overall_result = False
                failures.append((endpoint, reason))

    return overall_result, failures


class CCSimpleHttpServer(HTTPServer):
    """
    Simple http server to handle requests from the clients.
    """

    daemon_threads = False
    address_family = socket.AF_INET  # IPv4

    # The size of the request queue. If it takes a long time to process
    # a single request, any requests that arrive while the server is busy are
    # placed into a queue, up to request_queue_size requests [1].
    # The default value of 5 is not sufficient for production grade servers,
    # so we increase it to 511.
    # Apache [2] and Nginx webservers use 511 as the default backlog size
    # for historical and practical reasons.
    # [1] https://docs.python.org/3/library/socketserver.html
    # [2] https://httpd.apache.org/docs/2.4/mod/mpm_common.html#listenbacklog
    request_queue_size = 511

    def __init__(self,
                 server_address,
                 RequestHandlerClass,
                 config_directory,
                 workspace_directory,
                 product_db_sql_server,
                 pckg_data,
                 context,
                 check_env,
                 manager: session_manager.SessionManager,
                 machine_id: str,
                 task_queue: Queue,
                 task_pipes,
                 server_shutdown_flag: Value):

        LOG.debug("Initializing HTTP server...")

        self.config_directory = config_directory
        self.workspace_directory = workspace_directory
        self.www_root = pckg_data['www_root']
        self.doc_root = pckg_data['doc_root']
        self.version = pckg_data['version']
        self.context = context
        self.check_env = check_env
        self.manager = manager
        self.address, self.port = server_address
        self.__products = {}

        # Create a database engine for the configuration database.
        LOG.debug("Creating database engine for CONFIG DATABASE...")
        self.__engine = product_db_sql_server.create_engine()
        self.config_session = sessionmaker(bind=self.__engine)
        self.manager.set_database_connection(self.config_session)

        self.__task_queue = task_queue
        self.task_manager = BackgroundTaskManager(
            task_queue, task_pipes, self.config_session, self.check_env,
            server_shutdown_flag, machine_id,
            pathlib.Path(self.context.codechecker_workspace))

        # Load the initial list of products and set up the server.
        cfg_sess = self.config_session()
        permissions.initialise_defaults('SYSTEM', {
            'config_db_session': cfg_sess
        })

        self.cfg_sess_private = cfg_sess

        products = cfg_sess.query(ORMProduct).all()
        for product in products:
            self.add_product(product)
            permissions.initialise_defaults('PRODUCT', {
                'config_db_session': cfg_sess,
                'productID': product.id
            })
        cfg_sess.commit()
        cfg_sess.close()

        try:
            HTTPServer.__init__(self, (self.address, self.port),
                                RequestHandlerClass,
                                bind_and_activate=True)
            ssl_key_file = os.path.join(config_directory, "key.pem")
            ssl_cert_file = os.path.join(config_directory, "cert.pem")

            self.configure_keepalive()

            self.ssl_enabled = os.path.isfile(ssl_key_file) and \
                os.path.isfile(ssl_cert_file)

            if self.ssl_enabled:
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
                         "not found!", ssl_key_file, ssl_cert_file)
                LOG.info("Falling back to simple, insecure HTTP.")

        except Exception as e:
            LOG.error("Couldn't start the server: %s", e.__str__())
            raise

        # If the server was started with the port 0, the OS will pick an
        # available port.
        # For this reason, we will update the port variable after server
        # ininitialisation.
        self.port = self.socket.getsockname()[1]

    @property
    def formatted_address(self) -> str:
        return f"{str(self.address)}:{self.port}"

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
        """Terminates the server and releases associated resources."""
        try:
            self.server_close()
            self.__task_queue.close()
            self.__task_queue.join_thread()
            self.__engine.dispose()

            sys.exit(128 + signal.SIGINT)
        except Exception as ex:
            LOG.error("Failed to shut down the WEB server!")
            LOG.error(str(ex))
            sys.exit(1)

    def serve_forever_with_shutdown_handler(self):
        """
        Calls `HTTPServer.serve_forever` but handles SIGINT (2) signals
        gracefully such that the open resources are properly cleaned up.
        """
        def _handler(signum: int, _frame):
            if signum not in [signal.SIGINT]:
                signal_log(LOG, "ERROR", "Signal "
                           f"<{signal.Signals(signum).name} ({signum})> "
                           "handling attempted by "
                           "'serve_forever_with_shutdown_handler'!")
                return

            signal_log(LOG, "DEBUG", f"{os.getpid()}: Received "
                       f"{signal.Signals(signum).name} ({signum}), "
                       "performing shutdown ...")
            self.terminate()

        signal.signal(signal.SIGINT, _handler)
        return self.serve_forever()

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

        prod = Product(orm_product.id,
                       orm_product.endpoint,
                       orm_product.display_name,
                       orm_product.connection,
                       self.context,
                       self.check_env)

        # Update the product database status.
        prod.connect()

        if prod.db_status == DBStatus.FAILED_TO_CONNECT:
            LOG.debug(
                "Failed to connect to database for product '%s'",
                orm_product.endpoint)
            return

        if prod.db_status == DBStatus.SCHEMA_MISSING and init_db:
            LOG.debug("Schema was missing in the database. Initializing new")
            prod.connect(init_db=True)

        # The "num_of_runs" column of the config database is shown on the
        # product page of the web interface. This is intentionally redundant
        # with a simple query that would count the number of runs in a product:
        # measurements have proven that this caching significantly improves
        # responsibility.
        # This field is incremented whenever a run is added to a product, and
        # decreased when run(s) are removed. However, if these numbers ever
        # diverge, the product page and the bottom right of the run page would
        # display different run counts. To help on this, the num_of_runs column
        # is updated at every server startup.
        # FIXME: Pylint emits a false positive here, and states that
        # session_factory() is not callable, because it initializes to None.
        # More on this:
        # https://github.com/Ericsson/codechecker/pull/3733#issuecomment-1235304179
        # https://github.com/PyCQA/pylint/issues/6005
        orm_product.num_of_runs = \
            prod.session_factory().query(func.count(Run.id)).one_or_none()[0] \
            # pylint: disable=not-callable

        self.__products[prod.endpoint] = prod

    def is_database_used(self, conn):
        """
        Returns bool whether the given database is already connected to by
        the server.
        """

        # get the database name from the database connection args
        driver = \
            'pysqlite' if conn.connection.engine == 'sqlite' else 'psycopg2'

        # create a tuple of database that is going to be added for comparison
        to_add = (
            f"{conn.connection.engine}+{driver}",
            conn.connection.database,
            conn.connection.host,
            conn.connection.port)

        # create a tuple of database that is already connected for comparison
        def to_tuple(product):
            url = make_url(product.connection)
            return url.drivername, url.database, url.host, url.port
        # creates a list of currently connected databases
        current_connected_databases = list(map(
            to_tuple,
            self.cfg_sess_private.query(ORMProduct).all()))

        self.cfg_sess_private.commit()
        self.cfg_sess_private.close()

        # the config database counts as an open database as well
        cfg_url = self.__engine.url
        cfg_entry = (cfg_url.drivername, cfg_url.database, cfg_url.host,
                     cfg_url.port)
        current_connected_databases.append(cfg_entry)

        # True if found, False otherwise
        return to_add in current_connected_databases

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
            raise ValueError(
                f"The product with the given endpoint '{endpoint}' does "
                "not exist!")

        LOG.info("Disconnecting product '%s'", endpoint)
        product.teardown()

        del self.__products[endpoint]

    def remove_products_except(self, endpoints_to_keep):
        """
        Removes EVERY product connection from the server except those
        endpoints specified in :endpoints_to_keep.
        """
        for ep in list(self.__products):
            if ep not in endpoints_to_keep:
                self.remove_product(ep)


class CCSimpleHttpServerIPv6(CCSimpleHttpServer):
    """
    CodeChecker HTTP simple server that listens over an IPv6 socket.
    """

    address_family = socket.AF_INET6

    @property
    def formatted_address(self) -> str:
        return f"[{str(self.address)}]:{self.port}"


def start_server(config_directory: str, workspace_directory: str,
                 package_data, port: int, config_sql_server,
                 listen_address: str, force_auth: bool,
                 skip_db_cleanup: bool, context, check_env,
                 machine_id: str,
                 api_handler_processes: Optional[int],
                 task_worker_processes: Optional[int]) -> int:
    """
    Starts the HTTP server to handle Web client and Thrift requests, execute
    background jobs.
    """
    LOG.debug("Starting CodeChecker server...")

    # The root user file is DEPRECATED AND IGNORED
    root_file = os.path.join(config_directory, 'root.user')
    if os.path.exists(root_file):
        LOG.warning("The 'root.user' file:  %s"
                    " is deprecated and ignored. If you want to"
                    " setup an initial user with SUPER_USER permission,"
                    " configure the super_user field in the server_config.json"
                    " as described in the documentation."
                    " To get rid off this warning,"
                    " simply delete the root.user file.",
                    root_file)
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

    server_secrets_file = os.path.join(config_directory, 'server_secrets.json')

    try:
        manager = session_manager.SessionManager(
            server_cfg_file,
            server_secrets_file,
            force_auth,
            api_handler_processes,
            task_worker_processes)

    except IOError as ioerr:
        LOG.debug(ioerr)
        LOG.error("The server's configuration file "
                  "is missing or can not be read!")
        sys.exit(1)
    except ValueError as verr:
        LOG.error(verr)
        sys.exit(1)

    if not skip_db_cleanup:
        all_success, fails = _do_db_cleanups(config_sql_server,
                                             context,
                                             check_env)
        if not all_success:
            LOG.error("Failed to perform automatic cleanup on %d products! "
                      "Earlier logs might contain additional detailed "
                      "reasoning.\n\t* %s", len(fails),
                      "\n\t* ".join(
                          (f"'{ep}' ({reason})" for (ep, reason) in fails)
                      ))
    else:
        LOG.debug("Skipping db_cleanup, as requested.")

    api_processes: Dict[int, Process] = {}
    requested_api_threads = cast(int, manager.worker_processes) \
        or cpu_count()

    bg_processes: Dict[int, Process] = {}
    requested_bg_threads = cast(int,
                                manager.background_worker_processes)
    # Note that Queue under the hood uses OS-level primitives such as a socket
    # or a pipe, where the read-write buffers have a **LIMITED** capacity, and
    # are usually **NOT** backed by the full amount of available system memory.
    bg_task_queue: Queue = Queue()
    is_server_shutting_down = Value('B', False)

    sync_manager = SyncManager()
    sync_manager.start()
    task_pipes = sync_manager.dict()

    def _cleanup_incomplete_tasks(action: str) -> int:
        config_db = config_sql_server.create_engine()
        config_session_factory = sessionmaker(bind=config_db)
        task_manager = BackgroundTaskManager(
            bg_task_queue, task_pipes, config_session_factory, check_env,
            is_server_shutting_down, machine_id,
            pathlib.Path(context.codechecker_workspace))

        try:
            task_manager.destroy_all_temporary_data()
        except OSError:
            LOG.warning("Clearing task-temporary storage space failed!")
            import traceback
            traceback.print_exc()

        try:
            return task_manager.drop_all_incomplete_tasks(action)
        finally:
            config_db.dispose()

    dropped_tasks = _cleanup_incomplete_tasks(
        "New server started with the same machine_id, assuming the old "
        "server is dead and won't be able to finish the task.")
    if dropped_tasks:
        LOG.info("At server startup, dropped %d background tasks left behind "
                 "by a previous server instance matching machine ID '%s'.",
                 dropped_tasks, machine_id)

    server_clazz = CCSimpleHttpServer
    if ':' in listen_address:
        # IPv6 address specified for listening.
        # FIXME: Python>=3.8 automatically handles IPv6 if ':' is in the bind
        # address, see https://bugs.python.org/issue24209.
        server_clazz = CCSimpleHttpServerIPv6

    http_server = server_clazz((listen_address, port),
                               RequestHandler,
                               config_directory,
                               workspace_directory,
                               config_sql_server,
                               package_data,
                               context,
                               check_env,
                               manager,
                               machine_id,
                               bg_task_queue,
                               task_pipes,
                               is_server_shutting_down)

    try:
        instance_manager.register(os.getpid(),
                                  os.path.abspath(
                                      context.codechecker_workspace),
                                  port)
    except IOError as ex:
        LOG.debug(ex.strerror)

    def unregister_handler(pid):
        # Handle errors during instance unregistration.
        # The workspace might be removed so updating the config content might
        # fail.
        try:
            instance_manager.unregister(pid)
        except IOError as ex:
            LOG.debug(ex.strerror)

    atexit.register(unregister_handler, os.getpid())

    def _start_process_with_no_signal_handling(**kwargs):
        """
        Starts a `multiprocessing.Process` in a context where the signal
        handling is temporarily disabled, such that the child process does not
        inherit any signal handling from the parent.

        Child processes spawned after the main process set up its signals
        MUST NOT inherit the signal handling because that would result in
        multiple children firing on the SIGTERM handler, for example.

        For this reason, we temporarily disable the signal handling here by
        returning to the initial defaults, and then restore the main process's
        signal handling to be the usual one.
        """
        signals_to_disable = [signal.SIGINT, signal.SIGTERM]
        if sys.platform != "win32":
            signals_to_disable += [signal.SIGCHLD, signal.SIGHUP]

        existing_signal_handlers = {}
        for signum in signals_to_disable:
            existing_signal_handlers[signum] = signal.signal(
                signum, signal.SIG_DFL)

        p = Process(**kwargs)
        p.start()

        for signum in signals_to_disable:
            signal.signal(signum, existing_signal_handlers[signum])

        return p

    # Save a process-wide but not shared counter in the main process for how
    # many subprocesses of each kind had been spawned, as this will be used in
    # the internal naming of the workers.
    spawned_api_proc_count: int = 0
    spawned_bg_proc_count: int = 0

    def spawn_api_process():
        """Starts a single HTTP API worker process for CodeChecker server."""
        nonlocal spawned_api_proc_count
        spawned_api_proc_count += 1

        p = _start_process_with_no_signal_handling(
            target=http_server.serve_forever_with_shutdown_handler,
            name=f"CodeChecker-API-{spawned_api_proc_count}")
        api_processes[cast(int, p.pid)] = p
        signal_log(LOG, "DEBUG", f"API handler child process {p.pid} started!")
        return p

    LOG.info("Using %d API request handler processes ...",
             requested_api_threads)
    for _ in range(requested_api_threads):
        spawn_api_process()

    def spawn_bg_process():
        """Starts a single Task worker process for CodeChecker server."""
        nonlocal spawned_bg_proc_count
        spawned_bg_proc_count += 1

        p = _start_process_with_no_signal_handling(
            target=background_task_executor,
            args=(bg_task_queue,
                  task_pipes,
                  config_sql_server,
                  check_env,
                  is_server_shutting_down,
                  machine_id,
                  ),
            name=f"CodeChecker-Task-{spawned_bg_proc_count}")
        bg_processes[cast(int, p.pid)] = p
        signal_log(LOG, "DEBUG", f"Task child process {p.pid} started!")
        return p

    LOG.info("Using %d Task worker processes ...", requested_bg_threads)
    for _ in range(requested_bg_threads):
        spawn_bg_process()

    termination_signal_timestamp = Value('d', 0)

    def forced_termination_signal_handler(signum: int, _frame):
        """
        Handle SIGINT (2) and SIGTERM (15) received a second time to stop the
        server ungracefully.
        """
        if signum not in [signal.SIGINT, signal.SIGTERM]:
            signal_log(LOG, "ERROR", "Signal "
                       f"<{signal.Signals(signum).name} ({signum})> "
                       "handling attempted by "
                       "'forced_termination_signal_handler'!")
            return
        if not is_server_shutting_down.value or \
                abs(termination_signal_timestamp.value) <= \
                sys.float_info.epsilon:
            return
        if time.time() - termination_signal_timestamp.value <= 2.0:
            # Allow some time to pass between the handling of the normal
            # termination vs. doing something in the "forced" handler, because
            # a human's ^C keypress in a terminal can generate multiple SIGINTs
            # in a quick succession.
            return

        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

        signal_log(LOG, "WARNING", "Termination signal "
                   f"<{signal.Signals(signum).name} ({signum})> "
                   "received a second time, **FORCE** killing the WEB server "
                   f"on [{http_server.formatted_address}] ...")

        for p in list(api_processes.values()) + list(bg_processes.values()):
            try:
                p.kill()
            except (OSError, ValueError):
                pass

        # No mercy this time.
        sys.exit(128 + signum)

    exit_code = Value('B', 0)

    def termination_signal_handler(signum: int, _frame):
        """
        Handle SIGINT (2) and SIGTERM (15) to stop the server gracefully.
        """
        # Debounce termination signals at this point.
        signal.signal(signal.SIGINT, forced_termination_signal_handler)
        signal.signal(signal.SIGTERM, forced_termination_signal_handler)

        if is_server_shutting_down.value:
            return
        if signum not in [signal.SIGINT, signal.SIGTERM]:
            signal_log(LOG, "ERROR", "Signal "
                       f"<{signal.Signals(signum).name} ({signum})> "
                       "handling attempted by 'termination_signal_handler'!")
            return

        is_server_shutting_down.value = True
        termination_signal_timestamp.value = time.time()

        exit_code.value = 128 + signum
        signal_log(LOG, "INFO", "Shutting down the WEB server on "
                   f"[{http_server.formatted_address}] ... "
                   "Please allow some time for graceful clean-up!")

        # Terminate child processes.
        # For these subprocesses, let the processes properly clean up after
        # themselves in a graceful shutdown scenario.
        # For this reason, we fire a bunch of SIGHUPs first, indicating
        # that the main server process wants to exit, and then wait for
        # the children to die once all of them got the signal.
        for pid in api_processes:
            try:
                signal_log(LOG, "DEBUG", f"SIGINT! API child PID: {pid} ...")
                os.kill(pid, signal.SIGINT)
            except (OSError, ValueError):
                pass
        for pid in list(api_processes.keys()):
            p = api_processes[pid]
            try:
                signal_log(LOG, "DEBUG", f"join() API child PID: {pid} ...")
                p.join()
                p.close()
            except (OSError, ValueError):
                pass
            finally:
                del api_processes[pid]

        bg_task_queue.close()
        bg_task_queue.join_thread()
        for pid in bg_processes:
            try:
                signal_log(LOG, "DEBUG", f"SIGHUP! Task child PID: {pid} ...")
                os.kill(pid, signal.SIGHUP)
            except (OSError, ValueError):
                pass
        for pid in list(bg_processes.keys()):
            p = bg_processes[pid]
            try:
                signal_log(LOG, "DEBUG", f"join() Task child PID: {pid} ...")
                p.join()
                p.close()
            except (OSError, ValueError):
                pass
            finally:
                del bg_processes[pid]

    def reload_signal_handler(signum: int, _frame):
        """
        Handle SIGHUP (1) to reload the server's configuration file to memory.
        """
        if signum not in [signal.SIGHUP]:
            signal_log(LOG, "ERROR", "Signal "
                       f"<{signal.Signals(signum).name} ({signum})> "
                       "handling attempted by 'reload_signal_handler'!")
            return

        signal_log(LOG, "INFO",
                   "Received signal to reload server configuration ...")

        manager.reload_config()

        signal_log(LOG, "INFO", "Server configuration reload: Done.")

    sigchild_event_counter = Value('I', 0)
    is_already_handling_sigchild = Value('B', False)

    def child_signal_handler(signum: int, _frame):
        """
        Handle SIGCHLD (17) that signals a child process's interruption or
        death by creating a new child to ensure that the requested number of
        workers are always alive.
        """
        if is_already_handling_sigchild.value:
            # Do not perform this handler recursively to prevent spawning too
            # many children.
            return
        if is_server_shutting_down.value:
            # Do not handle SIGCHLD events during normal shutdown, because
            # our own subprocess termination calls would fire this handler.
            return
        if signum not in [signal.SIGCHLD]:
            signal_log(LOG, "ERROR", "Signal "
                       f"<{signal.Signals(signum).name} ({signum})> "
                       "handling attempted by 'child_signal_handler'!")
            return

        is_already_handling_sigchild.value = True

        force_slow_path: bool = False
        event_counter: int = sigchild_event_counter.value
        if event_counter >= \
                min(requested_api_threads, requested_bg_threads) // 2:
            force_slow_path = True
        else:
            sigchild_event_counter.value = event_counter + 1

        # How many new processes need to be spawned for each type of worker
        # process?
        spawn_needs: Counter = Counter()

        def _check_process_one(kind: str, proclist: Dict[int, Process],
                               pid: int):
            try:
                p = proclist[pid]
            except KeyError:
                return

            # Unfortunately, "Process.is_alive()" cannot be used here, because
            # during the handling of SIGCHLD during a child's death, according
            # to the state of Python's data structures, the child is still
            # alive.
            # We run a low-level non-blocking wait again, which will
            # immediately return, but properly reap the child process if it has
            # terminated.
            try:
                _, status_signal = os.waitpid(pid, os.WNOHANG)
                if status_signal == 0:
                    # The process is still alive.
                    return
            except ChildProcessError:
                pass

            signal_log(LOG, "WARNING",
                       f"'{kind}' child process (PID {pid}, \"{p.name}\") "
                       "is not alive anymore!")
            spawn_needs[kind] += 1

            try:
                del proclist[pid]
            except KeyError:
                # Due to the bunching up of signals and that Python runs the
                # C-level signals with a custom logic inside the interpreter,
                # coupled with the fact that PIDs can be reused, the same PID
                # can be reported dead in a quick succession of signals,
                # resulting in a KeyError here.
                pass

        def _check_processes_many(kind: str, proclist: Dict[int, Process]):
            for pid in sorted(proclist.keys()):
                _check_process_one(kind, proclist, pid)

        # Try to find the type of the interrupted/dead process based on signal
        # information first.
        # This should be quicker and more deterministic.
        try:
            child_pid, child_signal = os.waitpid(-1, os.WNOHANG)
            if child_signal == 0:
                # Go to the slow path and check the children manually, we did
                # not receive a reply from waitpid() with an actual dead child.
                raise ChildProcessError()

            _check_process_one("api", api_processes, child_pid)
            _check_process_one("background", bg_processes, child_pid)
        except ChildProcessError:
            # We have not gotten a PID, or it was not found, so we do not know
            # who died; in this case, it is better to go on the slow path and
            # query all our children individually.
            spawn_needs.clear()  # Forces the Counter to be empty.

        if force_slow_path:
            # A clever sequence of child killings in variously sized batches
            # can easily result in missing a few signals here and there, and
            # missing a few dead children because 'os.waitpid()' allows us to
            # fall into a false "fast path" situation.
            # To remedy this, we every so often force a slow path to ensure
            # the number of worker processes is as close to the requested
            # amount of possible.

            # Forces the Counter to be empty, even if the fast path put an
            # entry in there.
            spawn_needs.clear()

        if not spawn_needs:
            _check_processes_many("api", api_processes)
            _check_processes_many("background", bg_processes)

        if force_slow_path:
            sigchild_event_counter.value = 0
            signal_log(LOG, "WARNING",
                       "Too many children died since last full status "
                       "check, performing one ...")

            # If we came into the handler with a "forced slow path" situation,
            # ensure that we spawn enough new processes to backfill the
            # missing amount, even if due to the flakyness of signal handling,
            # we might not have actually gotten "N" times SIGCHLD firings for
            # the death of N children, if they happened in a bundle situation,
            # e.g., kill N/4, then kill N/2, then kill 1 or 2, then kill the
            # remaining.
            spawn_needs["api"] = \
                util.clamp(0, requested_api_threads - len(api_processes),
                           requested_api_threads)
            spawn_needs["background"] = \
                util.clamp(0, requested_bg_threads - len(bg_processes),
                           requested_bg_threads)

        for kind, num in spawn_needs.items():
            signal_log(LOG, "INFO",
                       f"(Re-)starting {num} '{kind}' child process(es) ...")

            if kind == "api":
                for _ in range(num):
                    spawn_api_process()
            elif kind == "background":
                for _ in range(num):
                    spawn_bg_process()

        is_already_handling_sigchild.value = False

    signal.signal(signal.SIGINT, termination_signal_handler)
    signal.signal(signal.SIGTERM, termination_signal_handler)
    if sys.platform != "win32":
        signal.signal(signal.SIGCHLD, child_signal_handler)
        signal.signal(signal.SIGHUP, reload_signal_handler)

    LOG.info("Server waiting for client requests on [%s]",
             http_server.formatted_address)

    # We can not use a multiprocessing.Event here because that would result in
    # a deadlock, as the process waiting on the event is the one receiving the
    # shutdown signal.
    while not is_server_shutting_down.value:
        time.sleep(5)

    dropped_tasks = _cleanup_incomplete_tasks("Server shut down, task will "
                                              "be never be completed.")
    if dropped_tasks:
        LOG.info("At server shutdown, dropped %d background tasks that will "
                 "never be completed.", dropped_tasks)

    LOG.info("CodeChecker server quit (main process).")
    return exit_code.value


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
