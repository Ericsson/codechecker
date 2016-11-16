# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import os
import re
import socket
from functools import partial

import shared

from thrift.protocol import TBinaryProtocol
from thrift.protocol import TJSONProtocol
from thrift.transport import THttpClient
from thrift.transport import TSocket
from thrift.transport import TTransport


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
            if reqfailure.error_code == shared.ttypes.ErrorCode.DATABASE:

                print('Database error')
                print(str(reqfailure.message))
            else:
                print('Other error')
                print(str(reqfailure))

            return None

        except socket.error as serr:
            err_cause = os.strerror(serr.errno)
            print(str(serr))

            return None

        if self._auto_handle_connection:
            self._transport.close()
        return res

    def open_connection(self):
        assert not self._auto_handle_connection
        try:
            self._transport.open()
        except TTransport.TTransportException as terr:
            print(terr)
            raise

    def close_connection(self):
        assert not self._auto_handle_connection
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

    def __exit__(self, type, value, tb):
        self._transport.close()


class CCReportHelper(ThriftAPIHelper):

    def __init__(self, host, port, auto_handle_connection=True):
        # import only if necessary; some tests may not add this to PYTHONPATH
        from DBThriftAPI import CheckerReport

        transport = TTransport.TBufferedTransport(TSocket.TSocket(host, port))
        protocol = TBinaryProtocol.TBinaryProtocol(transport)
        client = CheckerReport.Client(protocol)
        super(CCReportHelper, self).__init__(transport, client,
                                             auto_handle_connection)


class CCViewerHelper(ThriftAPIHelper):

    def __init__(self, host, port, uri, auto_handle_connection=True,
                 session_token=None):
        # import only if necessary; some tests may not add this to PYTHONPATH
        from codechecker_lib import session_manager
        from codeCheckerDBAccess import codeCheckerDBAccess
        from codeCheckerDBAccess.constants import MAX_QUERY_SIZE

        self.max_query_size = MAX_QUERY_SIZE
        transport = THttpClient.THttpClient(host, port, uri)
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

    def __init__(self, host, port, uri, auto_handle_connection=True,
                 session_token=None):
        # import only if necessary; some tests may not add this to PYTHONPATH
        from codechecker_lib import session_manager
        from Authentication import codeCheckerAuthentication
        from Authentication.ttypes import HandshakeInformation

        transport = THttpClient.THttpClient(host, port, uri)
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


def get_all_run_results(client, run_id, sort_mode=[], filters=[]):
    """
    Get all the results for a run.
    Query limit limits the number of results can be got from the
    server in one API call.
    """

    offset = 0
    query_limit = client.max_query_size
    results = []
    while True:
        partial_res = client.getRunResults(run_id,
                                           query_limit,
                                           offset,
                                           sort_mode,
                                           filters)

        offset += len(partial_res)
        if len(partial_res) == 0:
            break
        results.extend(partial_res)

    return results
