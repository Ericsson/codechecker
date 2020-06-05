# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Unit tests for understanding product URLs. """


import unittest

from codechecker_client.product import expand_whole_protocol_and_port, \
    split_server_url, split_product_url


def expected_protocol(protocol=None, port=None):
    protocol, _ = expand_whole_protocol_and_port(protocol, port)
    return protocol


def expected_port(protocol=None, port=None):
    _, port = expand_whole_protocol_and_port(protocol, port)
    return port


class product_urlTest(unittest.TestCase):
    """
    Testing the product and server URL splitter.
    """

    def testFullURL(self):
        """
        Whole product URL understanding.
        """
        def test(host, port, name, protocol=None):
            url = ''.join([protocol + "://" if protocol else "",
                           host, ":", str(port), "/", name])

            sprotocol, shost, sport, sname = split_product_url(url)
            self.assertEqual(sprotocol, expected_protocol(protocol, port))
            self.assertEqual(shost, host)
            self.assertEqual(sport, expected_port(protocol, port))
            self.assertEqual(sname, name)

        test("localhost", 8001, "Default")
        test("[::1]", 8001, "Default")
        test("[f000:baa5::f00d]", 8080, "Foo")
        test("localhost", 8002, "MyProduct")
        test("another.server", 80, "CodeChecker", "http")
        test("very-secure.another.server", 443, "CodeChecker", "https")
        test("contains-a-port-overri.de", 1234, "PRD", "https")

    def testProductName(self):
        """
        Understanding only a product name specified.
        """
        def test(name, protocol=None):
            url = ''.join([protocol + "://" if protocol else "", name])

            sprotocol, shost, sport, sname = split_product_url(url)
            self.assertEqual(sprotocol, expected_protocol(protocol, None))
            self.assertEqual(shost, "localhost")
            self.assertEqual(sport, expected_port(protocol, None))
            self.assertEqual(sname, name)

        test("Default")
        test("Default", "http")
        test("MyProduct")
        test("Enterprise-Product", "https")

    def testHostAndProductName(self):
        """
        Understanding a host and a product name specified.
        """
        def test(host, name, protocol=None):
            url = ''.join([protocol + "://" if protocol else "",
                           host, "/", name])

            sprotocol, shost, sport, sname = split_product_url(url)
            self.assertEqual(sprotocol, expected_protocol(protocol, None))
            self.assertEqual(shost, host)
            self.assertEqual(sport, expected_port(protocol, None))
            self.assertEqual(sname, name)

        test("localhost", "Default")
        test("[::1]", "Default")
        test("[f000:baa5::f00d]", "Default")
        test("otherhost", "awesome123", "http")

        # 8080/MyProduct as if 8080 was a host name.
        test("8080", "MyProduct")
        test("super", "verygood", "https")

    def testBadProductNames(self):
        """
        Parser throws on bad product URLs?
        """

        with self.assertRaises(ValueError):
            split_product_url("123notaproductname")

        with self.assertRaises(ValueError):
            split_product_url("localhost//containsExtraChar")

        with self.assertRaises(ValueError):
            split_product_url("in:valid:format/product")

        with self.assertRaises(ValueError):
            split_product_url("localhost:12PortIsANumber34/Foo")

        with self.assertRaises(ValueError):
            split_product_url("codechecker://codecheker.com/Baz")

        with self.assertRaises(ValueError):
            # Make sure we don't understand "https://foobar.baz:1234" as
            # HTTPS, localhost, 443, and "foobar.baz:1234" product name.
            split_product_url("https://foobar.bar:1234")

        with self.assertRaises(ValueError):
            split_product_url("http://::1:8080/Default")

    def testFullServerURL(self):
        """
        Whole server URL understanding.
        """
        def test(host, port, protocol=None):
            url = ''.join([protocol + "://" if protocol else "",
                           host, ":", str(port)])

            sprotocol, shost, sport = split_server_url(url)
            self.assertEqual(sprotocol, expected_protocol(protocol, port))
            self.assertEqual(shost, host)
            self.assertEqual(sport, expected_port(protocol, port))

        test("localhost", 8001)
        test("localhost", 8002)
        test("1hostname.can.begin.with.digits", 9999)
        test("another.server", 80, "http")
        test("very-secure.another.server", 443, 'https')

        sprotocol, shost, sport = \
            split_server_url('https://someserver:1234/Product')
        self.assertEqual(sprotocol, 'https')
        self.assertEqual(shost, 'someserver')
        self.assertEqual(sport, 1234)

        sprotocol, shost, sport = \
            split_server_url('http://[::1]:1234/Product')
        self.assertEqual(sprotocol, 'http')
        self.assertEqual(shost, '[::1]')
        self.assertEqual(sport, 1234)

    def testHostname(self):
        """
        Understanding only a hostname specified for server URLs.
        """
        def test(host, protocol=None):
            url = ''.join([protocol + "://" if protocol else "", host])

            sprotocol, shost, sport = split_server_url(url)
            self.assertEqual(sprotocol, expected_protocol(protocol, None))
            self.assertEqual(shost, host)
            self.assertEqual(sport, expected_port(protocol, None))

        test("codechecker")  # Port: 8001
        test("[::1]")  # Port: 8001
        test("codechecker", "http")  # Port: 80
        test("codechecker.local")  # Port: 8001
        test("www.example.org", "https")  # Port: 443

    def testBadServerURLs(self):
        """
        Parser throws on bad server URLs?
        """

        with self.assertRaises(ValueError):
            split_server_url("in:valid:format")

        with self.assertRaises(ValueError):
            split_server_url("localhost:12PortIsANumber34")

        with self.assertRaises(ValueError):
            split_server_url("whatever://whatev.er")

        with self.assertRaises(ValueError):
            split_server_url("http://::1:8081")
