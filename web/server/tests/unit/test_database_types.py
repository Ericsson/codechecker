# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Unit tests for the custom database types' conversion routines."""
import unittest

from codechecker_server.database.types import zlib


class DatabaseZLibCompressedTypesTest(unittest.TestCase):
    """
    Testing that compressing and decompressing values with the ZLib wrapper
    adheres to idempotence.
    """

    dialect = "irrelevant"

    def _test(self, t, o):
        enc = t.process_bind_param(o, self.dialect)
        dec = t.process_result_value(enc, self.dialect)

        self.assertEqual(o, dec)

    def test_zlib_blob(self):
        t = zlib.ZLibCompressedBlob()
        self.assertEqual(t.process_bind_param(None, self.dialect), None)
        self.assertEqual(t.process_result_value(None, self.dialect), None)

        blob = ("CodeChecker is awesome!").encode()
        self._test(t, blob)

        t0 = zlib.ZLibCompressedBlob(compression_level=0)
        self._test(t0, blob)

    def test_zlib_header_mismatch(self):
        t = zlib.ZLibCompressedBlob()

        blob = ("CodeChecker is awesome!").encode()
        with self.assertRaises(ValueError):
            t.process_result_value(blob, self.dialect)

    def test_zlib_str(self):
        t = zlib.ZLibCompressedString()
        self.assertEqual(t.process_bind_param(None, self.dialect), None)
        self.assertEqual(t.process_result_value(None, self.dialect), None)

        self._test(t, "CodeChecker is awesome!")

    def test_zlib_kind_mismatch(self):
        tb = zlib.ZLibCompressedString()
        tt = zlib.ZLibCompressedString(kind="test")

        enc = tb.process_bind_param("This is a user-defined value!",
                                    self.dialect)
        with self.assertRaises(ValueError):
            tt.process_result_value(enc, self.dialect)

    def test_zlib_json(self):
        t = zlib.ZLibCompressedJSON()

        self._test(t, None)
        self._test(t, 42)
        self._test(t, 123.456)
        self._test(t, "CodeChecker is awesome!")
        self._test(t, ['a', 'b', 'c'])
        self._test(t, {'a': 1, 'b': "CodeChecker", 'c': [42, 42, 0]})
