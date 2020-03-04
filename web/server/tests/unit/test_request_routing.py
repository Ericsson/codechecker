# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" Unit tests for the request_routing module. """


import unittest

from codechecker_server.routing import split_client_GET_request
from codechecker_server.routing import split_client_POST_request


def GET(path):
    return split_client_GET_request("http://localhost:8001/" +
                                    path.lstrip('/'))


def POST(path):
    return split_client_POST_request("http://localhost:8001/" +
                                     path.lstrip('/'))


class request_routingTest(unittest.TestCase):
    """
    Testing the router that understands client request queries.
    """

    def testGET(self):
        """
        Test if the server properly splits query addresses for GET.
        """

        self.assertEqual(GET(''), (None, ''))
        self.assertEqual(GET('index.html'), (None, 'index.html'))
        self.assertEqual(GET('/scripts/codechecker.js'),
                         (None, 'scripts/codechecker.js'))

        self.assertEqual(GET('Default'), ('Default', ''))
        self.assertEqual(GET('Default/index.html'), ('Default', 'index.html'))

    def testPOST(self):
        """
        Test if the server properly splits query addresses for POST.
        """

        # The splitter returns None as these are invalid paths.
        # It is the server code's responsibility to give a 404 Not Found.
        self.assertIsNone(POST(''))
        self.assertIsNone(POST('CodeCheckerService'))

        # Raise an exception if URL is malformed, such as contains a
        # product-endpoint-like component which is badly encoded version
        # string.
        with self.assertRaises(Exception):
            POST('v6.0')
            POST('/v6/CodeCheckerService')

        self.assertEqual(POST('/v6.0/Authentication'),
                         (None, '6.0', 'Authentication'))

        self.assertEqual(POST('/DummyProduct/v0.0/FoobarService'),
                         ('DummyProduct', '0.0', 'FoobarService'))
