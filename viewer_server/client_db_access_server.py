# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Main viewer server starts a http server which handles thrift client
and browser requests.
"""
import errno
import os
import posixpath
import socket
import urllib
from multiprocessing.pool import ThreadPool

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from SimpleHTTPServer import SimpleHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler, \
        SimpleHTTPRequestHandler

from thrift.transport import TTransport
from thrift.protocol import TJSONProtocol

from codeCheckerDBAccess import codeCheckerDBAccess

from client_db_access_handler import ThriftRequestHandler

from codechecker_lib import logger
from codechecker_lib import database_handler

LOG = logger.get_new_logger('DB ACCESS')


class RequestHander(SimpleHTTPRequestHandler):
    """
    Handle thrift and browser requests
    Simply modified and extended version of SimpleHTTPRequestHandler
    """

    def __init__(self, request, client_address, server):

        self.sc_session = server.sc_session

        self.db_version_info = server.db_version_info

        BaseHTTPRequestHandler.__init__(self,
                                        request,
                                        client_address,
                                        server)

    def log_message(self, msg_format, *args):
        """ Silenting http server. """
        return

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
        itrans = TTransport.TBufferedTransport(itrans,
                                               int(self.headers[
                                                       'Content-Length']))
        otrans = TTransport.TMemoryBuffer()

        iprot = input_protocol_factory.getProtocol(itrans)
        oprot = output_protocol_factory.getProtocol(otrans)

        try:
            session = self.sc_session()
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
                 db_version_info):

        LOG.debug('Initializing HTTP server')

        self.www_root = pckg_data['www_root']
        self.doc_root = pckg_data['doc_root']
        self.checker_md_docs = pckg_data['checker_md_docs']
        self.checker_md_docs_map = pckg_data['checker_md_docs_map']
        self.suppress_handler = suppress_handler
        self.db_version_info = db_version_info
        self.__engine = database_handler.SQLServer.create_engine(db_conn_string)

        Session = scoped_session(sessionmaker())
        Session.configure(bind=self.__engine)
        self.sc_session = Session

        self.__request_handlers = ThreadPool(processes=10)

        HTTPServer.__init__(self, server_address,
                            RequestHandlerClass,
                            bind_and_activate=True)

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
                 not_host_only, db_version_info):
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
                                     RequestHander,
                                     db_conn_string,
                                     package_data,
                                     suppress_handler,
                                     db_version_info)

    LOG.info('Waiting for client requests on [' +
             access_server_host + ':' + str(port) + ']')
    http_server.serve_forever()
    LOG.info('done.')
