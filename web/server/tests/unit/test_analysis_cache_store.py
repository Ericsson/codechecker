# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Unit tests of the server side analysis cache storage (input validation,
cache key, REAPI storage format), against a mock bazel-remote server.
"""

import base64
import hashlib
import os
import sys
import tempfile
import unittest
import zlib

from codechecker_server.analysis_cache import bazel_remote, cache_store
from codechecker_server.analysis_cache import remote_execution_pb2 as reapi

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..',
                             'tests', 'libtest'))
# pylint: disable=wrong-import-position,import-error
from mock_bazel_remote import MockBazelRemote  # noqa: E402


KEY = 'a' * 64


class Content:
    def __init__(self, filename, content):
        self.filename = filename
        self.content = content


def enc(data: bytes) -> str:
    return base64.b64encode(zlib.compress(data)).decode()


class AnalysisCacheStoreTest(unittest.TestCase):

    def setUp(self):
        self.mock = MockBazelRemote().start()
        self.client = bazel_remote.BazelRemoteClient(self.mock.url,
                                                     timeout=5)
        self.config = cache_store.CacheConfig.from_dict(
            {'url': self.mock.url})

    def tearDown(self):
        self.mock.stop()

    def __write(self, contents, product='P', key=KEY):
        cache_store.write_entry(self.client, product, key, contents,
                                self.config)

    def __read(self, product='P', key=KEY):
        return cache_store.read_entry(self.client, product, key,
                                      self.config)

    def test_config(self):
        with self.assertRaises(cache_store.CacheNotConfiguredError):
            cache_store.CacheConfig.from_dict(None)
        with self.assertRaises(cache_store.CacheNotConfiguredError):
            cache_store.CacheConfig.from_dict({'url': None})

        cfg = cache_store.CacheConfig.from_dict(
            {'url': 'http://x', 'max_content_size': 'bad',
             'max_files_per_entry': -1})
        self.assertEqual(cfg.max_content_size,
                         cache_store.DEFAULT_MAX_CONTENT_SIZE)
        self.assertEqual(cfg.max_files_per_entry,
                         cache_store.DEFAULT_MAX_FILES_PER_ENTRY)

    def test_write_read(self):
        contents = [Content('result.plist', enc(b'<plist/>')),
                    Content('stdout.txt', enc(b'out'))]
        self.__write(contents)

        # Stored in the REAPI format: encoded blobs in the CAS, an
        # ActionResult in the AC.
        self.assertEqual(len(self.mock.cas), 2)
        ac_key = cache_store.ac_key('P', KEY)
        result = reapi.ActionResult.FromString(self.mock.ac[ac_key])
        self.assertEqual([f.path for f in result.output_files],
                         ['result.plist', 'stdout.txt'])
        blob = contents[0].content.encode()
        self.assertEqual(result.output_files[0].digest.hash,
                         hashlib.sha256(blob).hexdigest())
        self.assertEqual(result.output_files[0].digest.size_bytes, len(blob))

        # The content is returned unchanged (still encoded).
        self.assertEqual(self.__read(),
                         [(c.filename, c.content) for c in contents])

    def test_product_isolation(self):
        self.__write([Content('result.plist', enc(b'x'))], product='P1')
        self.assertTrue(self.__read(product='P1'))
        self.assertEqual(self.__read(product='P2'), [])
        self.assertNotEqual(cache_store.ac_key('P1', KEY),
                            cache_store.ac_key('P2', KEY))

    def test_miss(self):
        self.assertEqual(self.__read(), [])

    def test_missing_cas_blob_is_miss(self):
        self.__write([Content('result.plist', enc(b'x')),
                      Content('stdout.txt', enc(b'y'))])
        # Simulate the LRU eviction of one blob: no partial result.
        self.mock.cas.pop(next(iter(self.mock.cas)))
        self.assertEqual(self.__read(), [])

    def test_digest_mismatch_is_miss(self):
        self.__write([Content('result.plist', enc(b'x'))])
        key = next(iter(self.mock.cas))
        self.mock.cas[key] = b'tampered'
        self.assertEqual(self.__read(), [])

    def test_invalid_action_result_is_miss(self):
        ac_key = cache_store.ac_key('P', KEY)
        self.mock.ac[ac_key] = b'\xff\xff\xff'
        self.assertEqual(self.__read(), [])

        # Valid protobuf, but invalid file name.
        bad = reapi.ActionResult(output_files=[reapi.OutputFile(
            path='../x', digest=reapi.Digest(hash='b' * 64, size_bytes=1))])
        self.mock.ac[ac_key] = bad.SerializeToString()
        self.assertEqual(self.__read(), [])

    def test_invalid_key(self):
        for key in ['A' * 64, 'a' * 63, 'g' * 64, '', None, '../' + 'a' * 61]:
            with self.assertRaises(cache_store.CacheValidationError):
                self.__write([Content('result.plist', enc(b'x'))], key=key)
            with self.assertRaises(cache_store.CacheValidationError):
                self.__read(key=key)

    def test_invalid_contents(self):
        good = enc(b'x')
        invalid = [
            [],
            [Content('a', good), Content('b', good), Content('c', good),
             Content('d', good)],
            [Content('result.plist', good), Content('result.plist', good)],
            [Content('../result.plist', good)],
            [Content('dir/result.plist', good)],
            [Content('dir\\result.plist', good)],
            [Content('..', good)],
            [Content('.', good)],
            [Content('', good)],
            [Content('a b', good)],
            [Content('x' * 256, good)],
            [Content('result.plist', None)],
            [Content('result.plist', '!!! not base64')],
        ]
        for contents in invalid:
            with self.assertRaises(cache_store.CacheValidationError):
                self.__write(contents)
        self.assertEqual(self.mock.cas, {})
        self.assertEqual(self.mock.ac, {})

    def test_content_size_limit(self):
        config = cache_store.CacheConfig.from_dict(
            {'url': self.mock.url, 'max_content_size': 100})
        with self.assertRaises(cache_store.CacheValidationError):
            cache_store.write_entry(
                self.client, 'P', KEY,
                [Content('result.plist', 'A' * 104)], config)

        # The server does not decompress: a small, highly compressed content
        # is accepted.
        bomb = enc(b'\0' * (1024 * 1024))
        self.assertLess(len(bomb), 100 * 1024)
        self.__write([Content('result.plist', bomb)])

    def test_backend_error(self):
        self.mock.fail_status = 500
        with self.assertRaises(bazel_remote.BazelRemoteError):
            self.__write([Content('result.plist', enc(b'x'))])
        with self.assertRaises(bazel_remote.BazelRemoteError):
            self.__read()

    def test_ac_written_after_cas(self):
        self.mock.fail_status = None
        self.__write([Content('result.plist', enc(b'x')),
                      Content('stdout.txt', enc(b'y'))])
        puts = [path for method, path in self.mock.requests
                if method == 'PUT']
        self.assertTrue(puts[-1].startswith('/ac/'))
        self.assertTrue(all(p.startswith('/cas/') for p in puts[:-1]))

    def test_basic_auth(self):
        mock = MockBazelRemote(user='u', password='secret').start()
        try:
            with tempfile.NamedTemporaryFile('w', delete=False) as f:
                f.write('secret\n')
            client = bazel_remote.get_client(mock.url, 'u', f.name, 5)
            cache_store.write_entry(client, 'P', KEY,
                                    [Content('result.plist', enc(b'x'))],
                                    self.config)
            self.assertTrue(cache_store.read_entry(client, 'P', KEY,
                                                   self.config))

            no_auth = bazel_remote.BazelRemoteClient(mock.url, timeout=5)
            with self.assertRaises(bazel_remote.BazelRemoteError):
                cache_store.read_entry(no_auth, 'P', KEY, self.config)
        finally:
            os.remove(f.name)
            mock.stop()
