# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" Unit tests for understanding product URLs. """

import unittest

from libcodechecker.util import split_product_url


class product_urlTest(unittest.TestCase):
    """
    Testing the product URL splitter.
    """

    def testFullURL(self):
        """
        Whole product URL understanding.
        """
        def test(host, port, name, protocol=None):
            url = ''.join([protocol + "://" if protocol else "",
                           host, ":", str(port), "/", name])

            shost, sport, sname = split_product_url(url)
            self.assertEqual(shost, host)
            self.assertEqual(sport, port)
            self.assertEqual(sname, name)

        test("localhost", 8001, "Default")
        test("localhost", 8002, "MyProduct")
        test("another.server", 80, "CodeChecker", "http")
        test("very-secure.another.server", 443, "CodeChecker", "https")

    def testProductName(self):
        """
        Understanding only a product name specified.
        """
        def test(name, protocol=None):
            url = ''.join([protocol + "://" if protocol else "", name])

            shost, sport, sname = split_product_url(url)
            self.assertEqual(shost, "localhost")
            self.assertEqual(sport, 8001)
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

            shost, sport, sname = split_product_url(url)
            self.assertEqual(shost, host)
            self.assertEqual(sport, 8001)
            self.assertEqual(sname, name)

        test("localhost", "Default")
        test("otherhost", "awesome123", "http")

        # 8080/product as if 8080 was a host name.
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
