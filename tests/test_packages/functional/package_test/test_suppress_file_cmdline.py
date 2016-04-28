#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import json
import os
import unittest

from test_utils.thrift_client_to_db import CCViewerHelper


class RunResults(unittest.TestCase):

    _ccClient = None

    # selected runid for running the tests
    _runid = None

    def setUp(self):
        host = 'localhost'
        port = int(os.environ['CC_TEST_VIEWER_PORT'])
        uri = '/'
        self._testproject_data = json.loads(os.environ['CC_TEST_PROJECT_INFO'])
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = CCViewerHelper(host, port, uri)

    # -----------------------------------------------------
    def test_suppress_file_set_in_cmd(self):
        """
        server is started with a suppress file
        check if the api returns a non empty string
        tempfile is used for suppress file so name will change for each run
        """
        self.assertNotEquals(self._cc_client.getSuppressFile(),
                             '')
