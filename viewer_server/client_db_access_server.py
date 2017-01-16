# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Main viewer server starts a http server which handles thrift client
and browser requests
"""
import atexit
import base64
import errno
import os
import posixpath
import socket
import sys
import urllib
from multiprocessing.pool import ThreadPool

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session

try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from SimpleHTTPServer import SimpleHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler, \
        SimpleHTTPRequestHandler

from thrift import Thrift
from thrift.Thrift import TException
from thrift.transport import TTransport
from thrift.protocol import TJSONProtocol

import shared
from codeCheckerDBAccess import codeCheckerDBAccess
from codeCheckerDBAccess import constants
from codeCheckerDBAccess.ttypes import *
from Authentication import codeCheckerAuthentication
from Authentication import constants
from Authentication.ttypes import *

from client_db_access_handler import ThriftRequestHandler
from client_auth_handler import ThriftAuthHandler

from codechecker_lib import database_handler
from codechecker_lib import instance_manager
from codechecker_lib import session_manager
from codechecker_lib.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('DB ACCESS')


class RequestHandler(SimpleHTTPRequestHandler):
    """
    Handle thrift and browser requests
    Simply modified and extended version of SimpleHTTPRequestHandler
    """

    def __init__(self, request, client_address, server):
        self.sc_session = server.sc_session

        self.db_version_info = server.db_version_info
        self.manager = server.manager

        BaseHTTPRequestHandler.__init__(self,
                                        request,
                                        client_address,
                                        server)

    def log_message(self, msg_format, *args):
        """ Silenting http server. """
        return

    def check_auth_in_request(self):
        """
        Wrapper to handle authentication needs from both GET and POST requests.
        """

        if not self.manager.isEnabled():
            return True

        success = False

        # Authentication can happen in two possible ways:
        #
        # The user either presents a valid session cookie -- in this case, checking if
        # the session for the given cookie is valid

        client_host, client_port = self.client_address

        for k in self.headers.getheaders("Cookie"):
            split = k.split("; ")
            for cookie in split:
                values = cookie.split("=")
                if len(values) == 2 and \
                        values[0] == session_manager.SESSION_COOKIE_NAME:
                    if self.manager.is_valid(client_host, values[1], True):
                        # The session cookie contains valid data.
                        success = values[1]

        if not success:
            # Session cookie was invalid (or not found...)
            # Attempt to see if the browser has sent us an authentication request
            authHeader = self.headers.getheader("Authorization")
            if authHeader is not None and authHeader.startswith("Basic "):
                LOG.info("Client from " + client_host + ":" +
                         str(client_port) + " attempted authorization.")
                authString = base64.decodestring(
                    self.headers.getheader("Authorization").
                    replace("Basic ", ""))

                token = self.manager.create_or_get_session(client_host,
                                                           authString)
                if token:
                    LOG.info("Client from " + client_host + ":" +
                             str(client_port) + " successfully logged in")
                    return token

        # Else, access is still not granted.
        if not success:
            LOG.debug(client_host + ":" + str(client_port) +
                      " Invalid access, credentials not found " +
                      "- session refused.")
            return None

        return success

    def do_GET(self):
        authToken = self.check_auth_in_request()
        if authToken:
            self.send_response(200)
            if isinstance(authToken, str):
                self.send_header("Set-Cookie",
                                 session_manager.SESSION_COOKIE_NAME + "=" +
                                 authToken + "; Path=/")
            SimpleHTTPRequestHandler.do_GET(self)
        else:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="' +
                             self.manager.getRealm()["realm"] + '"')
            self.send_header("Content-type", "text/plain")
            self.send_header("Content-length", str(len(
                self.manager.getRealm()["error"])))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(self.manager.getRealm()["error"])

    def do_POST(self):
        """ Handling thrift messages. """
        client_host, client_port = self.client_address
        LOG.debug('Processing request from: ' +
                  client_host + ':' +
                  str(client_port))

        # Create new thrift handler.
        checker_md_docs = self.server.checker_md_docs
        checker_md_docs_map = self.server.checker_md_docs_map
        suppress_handler = self.server.suppress_handler

        protocol_factory = TJSONProtocol.TJSONProtocolFactory()
        input_protocol_factory = protocol_factory
        output_protocol_factory = protocol_factory

        itrans = TTransport.TFileObjectTransport(self.rfile)
        otrans = TTransport.TFileObjectTransport(self.wfile)
        itrans = TTransport.TBufferedTransport(itrans,
                                               int(self.headers[
                                                       'Content-Length']))
        otrans = TTransport.TMemoryBuffer()

        iprot = input_protocol_factory.getProtocol(itrans)
        oprot = output_protocol_factory.getProtocol(otrans)

        sess_token = self.check_auth_in_request()
        if self.path != '/Authentication' and not sess_token:
            # Bail out if the user is not authenticated...
            # This response has the possibility of melting down Thrift clients,
            # but the user is expected to properly authenticate first.

            LOG.debug(client_host + ":" + str(client_port) +
                      " Invalid access, credentials not found " +
                      "- session refused.")
            self.send_response(401)
            self.send_header("Content-type", "text/plain")
            self.send_header("Content-length", str(0))
            self.end_headers()

            return

        # Authentication is handled, we may now respond to the user.
        try:
            session = self.sc_session()
            acc_handler = ThriftRequestHandler(session,
                                               checker_md_docs,
                                               checker_md_docs_map,
                                               suppress_handler,
                                               self.db_version_info)

            if self.path == '/Authentication':
                # Authentication requests must be routed to a different handler.
                auth_handler = ThriftAuthHandler(self.manager,
                                                 client_host,
                                                 sess_token)
                processor = codeCheckerAuthentication.Processor(auth_handler)
            else:
                acc_handler = ThriftRequestHandler(session,
                                                   checker_md_docs,
                                                   checker_md_docs_map,
                                                   suppress_handler,
                                                   self.db_version_info)

                processor = codeCheckerDBAccess.Processor(acc_handler)

            processor.process(iprot, oprot)
            result = otrans.getvalue()

            self.sc_session.remove()

            self.send_response(200)
            self.send_header("content-type", "application/x-thrift")
            self.send_header("Content-Length", len(result))
            self.end_headers()
            self.wfile.write(result)
            return

        except Exception as exn:
            LOG.error(str(exn))
            self.send_error(404, "Request failed.")
            return

    def list_directory(self, path):
        """ Disable directory listing. """
        self.send_error(404, "No permission to list directory")
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
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path


class CCSimpleHttpServer(HTTPServer):
    """
    Simple http server to handle requests from the clients.
    """

    daemon_threads = False

    def __init__(self,
                 server_address,
                 RequestHandlerClass,
                 db_conn_string,
                 pckg_data,
                 suppress_handler,
                 db_version_info,
                 manager):

        LOG.debug('Initializing HTTP server')

        self.www_root = pckg_data['www_root']
        self.doc_root = pckg_data['doc_root']
        self.checker_md_docs = pckg_data['checker_md_docs']
        self.checker_md_docs_map = pckg_data['checker_md_docs_map']
        self.suppress_handler = suppress_handler
        self.db_version_info = db_version_info
        self.__engine = database_handler.SQLServer.create_engine(
            db_conn_string)

        Session = scoped_session(sessionmaker())
        Session.configure(bind=self.__engine)
        self.sc_session = Session
        self.manager = manager

        self.__request_handlers = ThreadPool(processes=10)

        try:
            HTTPServer.__init__(self, server_address,
                                RequestHandlerClass,
                                bind_and_activate=True)
        except Exception as e:
            LOG.error("Couldn't start the server: " + e.__str__())
            sys.exit(1)

    def process_request_thread(self, request, client_address):
        try:
            # Finish_request instatiates request handler class.
            self.finish_request(request, client_address)
            self.shutdown_request(request)
        except socket.error as serr:
            if serr[0] == errno.EPIPE:
                LOG.debug('Broken pipe')
                LOG.debug(serr)
                self.shutdown_request(request)

        except Exception as ex:
            LOG.debug(ex)
            self.handle_error(request, client_address)
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        self.__request_handlers.apply_async(self.process_request_thread,
                                            (request, client_address))


def start_server(package_data, port, db_conn_string, suppress_handler,
                 not_host_only, context):
    """
    Start http server to handle web client and thrift requests.
    """
    LOG.debug('Starting the codechecker DB access server')

    if not_host_only:
        access_server_host = ''
    else:
        access_server_host = 'localhost'

    LOG.debug('Suppressing to ' + str(suppress_handler.suppress_file))

    server_addr = (access_server_host, port)

    http_server = CCSimpleHttpServer(server_addr,
                                     RequestHandler,
                                     db_conn_string,
                                     package_data,
                                     suppress_handler,
                                     context.db_version_info,
                                     session_manager.SessionManager())

    instance_manager.register(os.getpid(),
                              os.path.abspath(context.codechecker_workspace),
                              port)

    LOG.info('Waiting for client requests on [' +
             access_server_host + ':' + str(port) + ']')

    atexit.register(instance_manager.unregister, os.getpid())
    http_server.serve_forever()
    LOG.info('Webserver quit.')
