# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Unit tests for the request_routing module. """


import unittest

from codechecker_server.routing import split_client_GET_request
from codechecker_server.routing import split_client_POST_request


def get(path, host="http://localhost:8001/"):
    return split_client_GET_request(host + path.lstrip('/'))


def post(path):
    return split_client_POST_request("http://localhost:8001/" +
                                     path.lstrip('/'))


class RequestRoutingTest(unittest.TestCase):
    """
    Testing the router that understands client request queries.
    """

    def test_get(self):
        """
        Test if the server properly splits query addresses for GET.
        """

        self.assertEqual(get(''), (None, ''))
        self.assertEqual(get('/', '//'), (None, ''))
        self.assertEqual(get('index.html'), (None, 'index.html'))
        self.assertEqual(get('/images/logo.png'),
                         (None, 'images/logo.png'))

        self.assertEqual(get('Default'), ('Default', ''))
        self.assertEqual(get('Default/index.html'), ('Default', 'index.html'))

    def test_post(self):
        """
        Test if the server properly splits query addresses for POST.
        """

        # The splitter returns (None, None, None) as these are invalid paths.
        # It is the server code's responsibility to give a 404 Not Found.
        self.assertEqual(post(''), (None, None, None))
        self.assertEqual(post('CodeCheckerService'), (None, None, None))
        self.assertEqual(post('v6.0'), (None, None, None))
        self.assertEqual(post('/v6.0/product/Authentication/Service'),
                         (None, None, None))

        self.assertEqual(post('/v6.0/Authentication'),
                         (None, '6.0', 'Authentication'))

        self.assertEqual(post('/DummyProduct/v6.0/FoobarService'),
                         ('DummyProduct', '6.0', 'FoobarService'))
