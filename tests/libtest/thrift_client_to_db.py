# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

from functools import partial
from libcodechecker import util
import os
import re
import socket

from thrift.protocol import TJSONProtocol
from thrift.transport import THttpClient
from thrift.transport import TTransport
from thrift.Thrift import TApplicationException

import shared

from libcodechecker.version import CLIENT_API as VERSION


class ThriftAPIHelper(object):

    def __init__(self, transport, client, auto_handle_connection=True):
        self._transport = transport
        self._client = client
        self._auto_handle_connection = auto_handle_connection

    def _thrift_client_call(self, func_name, *args, **kwargs):
        if self._auto_handle_connection:
            self._transport.open()
        func = getattr(self._client, func_name)
        try:
            res = func(*args, **kwargs)

        except shared.ttypes.RequestFailed as reqfailure:
            if reqfailure.errorCode == shared.ttypes.ErrorCode.GENERAL:
                print('Request failed')
                print(str(reqfailure.message))
            elif reqfailure.errorCode == shared.ttypes.ErrorCode.IOERROR:
                print('Server reported I/O error')
                print(str(reqfailure.message))
            elif reqfailure.errorCode == shared.ttypes.ErrorCode.DATABASE:
                print('Database error on server')
                print(str(reqfailure.message))
            elif reqfailure.errorCode == shared.ttypes.ErrorCode.AUTH_DENIED:
                print('Authentication denied')
                print(str(reqfailure.message))
            elif reqfailure.errorCode == shared.ttypes.ErrorCode.UNAUTHORIZED:
                print('Unauthorized to access')
                print(str(reqfailure.message))
            else:
                print('API call error ' + reqfailure.error_code +
                      ': ' + func_name)
                print(str(reqfailure))

            raise

        except TApplicationException as err:
            print(err.message)
            return None

        except socket.error as serr:
            err_cause = os.strerror(serr.errno)
            print(str(serr) + " " + err_cause)

            return None

        if self._auto_handle_connection:
            self._transport.close()
        return res

    def open_connection(self):
        if self._auto_handle_connection:
            raise IOError("Explicitly opened connection of auto-connecting "
                          "wrapper.")

        try:
            self._transport.open()
        except TTransport.TTransportException as terr:
            print(terr)
            raise

    def close_connection(self):
        if self._auto_handle_connection:
            raise IOError("Explicitly closed connection of auto-connecting "
                          "wrapper.")

        self._transport.close()

    def __getattr__(self, attr):
        return partial(self._thrift_client_call, attr)

    def __enter__(self):
        try:
            self._auto_handle_connection = False
            self._transport.open()
        except TTransport.TTransportException as terr:
            print(terr)
            raise
        return self

    def __exit__(self, exc_type, value, tb):
        self._transport.close()


class CCViewerHelper(ThriftAPIHelper):

    def __init__(self, protocol, host, port, product, endpoint,
                 auto_handle_connection=True, session_token=None):
        # Import only if necessary; some tests may not add this to PYTHONPATH.
        from libcodechecker import session_manager
        from codeCheckerDBAccess_v6 import codeCheckerDBAccess
        from codeCheckerDBAccess_v6.constants import MAX_QUERY_SIZE

        self.max_query_size = MAX_QUERY_SIZE
        url = util.create_product_url(protocol, host, port,
                                      '/' + product + '/v' +
                                      VERSION + endpoint)
        print("Setup viewer client: "+url)
        transport = THttpClient.THttpClient(url)
        protocol = TJSONProtocol.TJSONProtocol(transport)
        client = codeCheckerDBAccess.Client(protocol)
        if session_token:
            headers = {'Cookie': session_manager.SESSION_COOKIE_NAME +
                       "=" + session_token}
            transport.setCustomHeaders(headers)
        super(CCViewerHelper, self).__init__(transport,
                                             client, auto_handle_connection)

    def __getattr__(self, attr):
        is_getAll = re.match(r'(get)All(.*)$', attr)
        if is_getAll:
            func_name = is_getAll.group(1) + is_getAll.group(2)
            return partial(self._getAll_emu, func_name)
        else:
            return partial(self._thrift_client_call, attr)

    def _getAll_emu(self, func_name, *args):
        """
        Do not call the getAll* functions with keyword arguments,
        limit and offset must be the -4. / -3. positional arguments
        of the wrapped function.
        """

        func2call = partial(self._thrift_client_call, func_name)
        limit = self.max_query_size
        offset = 0
        results = []

        args = list(args)
        args[-2:-2] = [limit, offset]
        some_results = func2call(*args)

        while some_results:
            results += some_results
            offset += len(some_results)  # == min(limit, real limit)
            args[-4:-2] = [limit, offset]
            some_results = func2call(*args)

        return results


class CCAuthHelper(ThriftAPIHelper):

    def __init__(self, proto, host, port, uri, auto_handle_connection=True,
                 session_token=None):
        # Import only if necessary; some tests may not add this to PYTHONPATH.
        from libcodechecker import session_manager
        from Authentication_v6 import codeCheckerAuthentication
        url = util.create_product_url(proto, host, port,
                                      '/v' + VERSION + uri)
        transport = THttpClient.THttpClient(url)
        protocol = TJSONProtocol.TJSONProtocol(transport)
        client = codeCheckerAuthentication.Client(protocol)
        if session_token:
            headers = {'Cookie': session_manager.SESSION_COOKIE_NAME +
                       "=" + session_token}
            transport.setCustomHeaders(headers)
        super(CCAuthHelper, self).__init__(transport,
                                           client, auto_handle_connection)

    def __getattr__(self, attr):
        return partial(self._thrift_client_call, attr)


class CCProductHelper(ThriftAPIHelper):

    def __init__(self, proto, host, port, product,
                 uri, auto_handle_connection=True,
                 session_token=None):
        # Import only if necessary; some tests may not add this to PYTHONPATH.
        from libcodechecker import session_manager
        from ProductManagement_v6 import codeCheckerProductService
        full_uri = '/v' + VERSION + uri
        if product:
            full_uri = '/' + product + full_uri
        url = util.create_product_url(proto, host, port,
                                      full_uri)
        transport = THttpClient.THttpClient(url)
        protocol = TJSONProtocol.TJSONProtocol(transport)
        client = codeCheckerProductService.Client(protocol)
        if session_token:
            headers = {'Cookie': session_manager.SESSION_COOKIE_NAME +
                       "=" + session_token}
            transport.setCustomHeaders(headers)
        super(CCProductHelper, self).__init__(transport,
                                              client, auto_handle_connection)

    def __getattr__(self, attr):
        return partial(self._thrift_client_call, attr)


def get_all_run_results(client, run_id, sort_mode=None, filters=None):
    """
    Get all the results for a run.
    Query limit limits the number of results can be got from the
    server in one API call.
    """

    offset = 0
    query_limit = client.max_query_size
    results = []

    if not sort_mode:
        sort_mode = []

    while True:
        partial_res = client.getRunResults([run_id],
                                           query_limit,
                                           offset,
                                           sort_mode,
                                           filters,
                                           None)

        offset += len(partial_res)
        if len(partial_res) == 0:
            break
        results.extend(partial_res)

    return results


def get_viewer_client(product, port, host='localhost',
                      endpoint='/CodeCheckerService',
                      auto_handle_connection=True,
                      session_token=None, protocol='http'):

    return CCViewerHelper(protocol, host, port, product,
                          endpoint,
                          auto_handle_connection,
                          session_token)


def get_auth_client(port, host='localhost', uri='/Authentication',
                    auto_handle_connection=True, session_token=None,
                    protocol='http'):
    return CCAuthHelper(protocol, host, port, uri,
                        auto_handle_connection,
                        session_token)


def get_product_client(port, host='localhost', product=None, uri='/Products',
                       auto_handle_connection=True, session_token=None,
                       protocol='http'):
    return CCProductHelper(protocol, host, port, product, uri,
                           auto_handle_connection,
                           session_token)
