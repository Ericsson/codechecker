# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" Unit tests for understanding product URLs. """

import unittest

from libcodechecker.util import split_product_url
from libcodechecker.util import split_server_url


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
            self.assertEqual(sprotocol, protocol if protocol else "http")
            self.assertEqual(shost, host)
            self.assertEqual(sport, port)
            self.assertEqual(sname, name)

        test("localhost", 8001, "Default")
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
            self.assertEqual(sprotocol, protocol if protocol else "http")
            self.assertEqual(shost, "localhost")
            self.assertEqual(sport, 443 if protocol == 'https' else 8001)
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
            self.assertEqual(sprotocol, protocol if protocol else "http")
            self.assertEqual(shost, host)
            self.assertEqual(sport, 443 if protocol == 'https' else 8001)
            self.assertEqual(sname, name)

        test("localhost", "Default")
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

    def testFullServerURL(self):
        """
        Whole server URL understanding.
        """
        def test(host, port, protocol=None):
            url = ''.join([protocol + "://" if protocol else "",
                           host, ":", str(port)])

            sprotocol, shost, sport = split_server_url(url)
            self.assertEqual(sprotocol, protocol if protocol else "http")
            self.assertEqual(shost, host)
            self.assertEqual(sport, port)

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

    def testHostname(self):
        """
        Understanding only a hostname specified for server URLs.
        """
        def test(host, protocol=None):
            url = ''.join([protocol + "://" if protocol else "", host])

            sprotocol, shost, sport = split_server_url(url)
            self.assertEqual(sprotocol, protocol if protocol else "http")
            self.assertEqual(shost, host)
            self.assertEqual(sport, 443 if protocol == 'https' else 8001)

        test("codechecker")
        test("codechecker", "http")
        test("codechecker.local")
        test("www.example.org", "https")

    def testBadServerURLs(self):
        """
        Parser throws on bad server URLs?
        """

        with self.assertRaises(ValueError):
            split_server_url("in:valid:format")

        with self.assertRaises(ValueError):
            split_server_url("localhost:12PortIsANumber34")
