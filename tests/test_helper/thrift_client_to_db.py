#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import errno
import os
import socket
import sys
from functools import partial

from thrift.transport import THttpClient
from thrift.transport import TSocket
from thrift.transport import TTransport

from thrift.protocol import TBinaryProtocol
from thrift.protocol import TJSONProtocol
from thrift.protocol import TProtocol

import shared


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

                print('****************')
                print('Database error')
                print(str(reqfailure.message))
                print('****************')
            else:
                print('****************')
                print('Other error')
                print(str(reqfailure))
                print('****************')

            return None

        except socket.error as serr:
            err_cause = os.strerror(serr.errno)
            print('*****SOCKET ERROR***********')
            print(err_cause)
            print(str(serr))
            print('****************')

            return None

        if self._auto_handle_connection:
            self._transport.close()
        return res

    def open_connection(self):
        assert not self._auto_handle_connection
        self._transport.open()

    def close_connection(self):
        assert not self._auto_handle_connection
        self._transport.close()

    def __getattr__(self, attr):
        return partial(self._thrift_client_call, attr)

    def __enter__(self):
        self._auto_handle_connection = False
        self._transport.open()
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

    def __init__(self, host, port, uri, auto_handle_connection=True):
        # import only if necessary; some tests may not add this to PYTHONPATH
        from codeCheckerDBAccess import codeCheckerDBAccess
        from codeCheckerDBAccess.constants import MAX_QUERY_SIZE

        self.max_query_size = MAX_QUERY_SIZE
        transport = THttpClient.THttpClient(host, port, uri)
        protocol = TJSONProtocol.TJSONProtocol(transport)
        client = codeCheckerDBAccess.Client(protocol)
        super(CCViewerHelper, self).__init__(transport,
                                             client, auto_handle_connection)

    def getAllRunResults(self, runId, sortType=None, reportFilters=None):
        limit = self.max_query_size
        offset = 0
        results = []

        some_results = self.getRunResults(runId, limit, offset, sortType,
                                          reportFilters)
        while some_results:
            results += some_results
            offset += len(some_results)  # == min(limit, real limit)
            some_results = self.getRunResults(runId, limit, offset, sortType,
                                              reportFilters)

        return results
