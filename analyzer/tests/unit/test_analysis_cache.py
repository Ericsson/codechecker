# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Unit tests of the client side analysis cache library.
"""

import base64
import os
import shutil
import tempfile
import unittest
import zlib
from unittest import mock

from codechecker_analyzer import analysis_cache as ac


SETTINGS = {'protocol': 'http', 'host': 'h', 'port': 1, 'product': 'P',
            'session_token': None, 'source_root': '/work/src',
            'report_dir': '/tmp'}


class FakeClient:
    """ In-memory stand-in for the Thrift AnalysisCacheClient. """

    def __init__(self):
        self.store = {}
        self.fail = False
        self.writes = 0

    def read_cache(self, key):
        if self.fail:
            raise OSError("connection refused")
        return list(self.store.get(key, []))

    def write_cache(self, key, contents):
        if self.fail:
            raise OSError("connection refused")
        self.writes += 1
        self.store[key] = list(contents)


def session_with(client, **kwargs):
    settings = ac.CacheSettings(**{**SETTINGS, **kwargs})
    session = ac.CacheSession(settings)
    # pylint: disable=protected-access
    session._CacheSession__client = client
    return session


class InvocationKeyTest(unittest.TestCase):

    CMD = ['/usr/lib/ccache/clang', '--analyze', '-Qunused-arguments',
           '-o', '/work/reports/a.c_clangsa_123.plist',
           '-Xclang', '-analyzer-checker=core.DivideZero',
           '-I/work/src/include', '-I/work/src2/include',
           '-idirafter', '/usr/include', '/work/src/a.c']

    def test_sanitize(self):
        self.assertEqual(
            ac.sanitize_analyzer_cmd(self.CMD, '/work/src'),
            ['<ANALYZER>', '--analyze', '-Qunused-arguments',
             '-o', '<OUTPUT>',
             '-Xclang', '-analyzer-checker=core.DivideZero',
             '-I__SOURCE_ROOT__/include', '-I/work/src2/include',
             '-idirafter', '/usr/include', '__SOURCE_ROOT__/a.c'])

    def test_joined_output_flag(self):
        self.assertEqual(
            ac.sanitize_analyzer_cmd(['clang', '-o/x/y.plist'], None),
            ['<ANALYZER>', '-o<OUTPUT>'])

    def test_location_independent(self):
        moved = ['/usr/bin/clang', '--analyze', '-Qunused-arguments',
                 '-o', '/other/reports/a.c_clangsa_456.plist',
                 '-Xclang', '-analyzer-checker=core.DivideZero',
                 '-I/home/u/checkout/include', '-I/work/src2/include',
                 '-idirafter', '/usr/include', '/home/u/checkout/a.c']
        self.assertEqual(
            ac.analysis_invocation_key(self.CMD, '/work/src'),
            ac.analysis_invocation_key(moved, '/home/u/checkout'))

        # Paths outside of the source root stay location dependent.
        moved[8] = '-I/home/u/checkout2/include'
        self.assertNotEqual(
            ac.analysis_invocation_key(self.CMD, '/work/src'),
            ac.analysis_invocation_key(moved, '/home/u/checkout'))

    def test_shlex_join(self):
        key = ac.analysis_invocation_key(['clang', '-DX=a b', 'f.c'], None)
        self.assertEqual(key, "'<ANALYZER>' '-DX=a b' f.c")

    def test_input_not_modified(self):
        cmd = list(self.CMD)
        ac.sanitize_analyzer_cmd(cmd, '/work/src')
        self.assertEqual(cmd, self.CMD)

    def test_analysis_key(self):
        key = ac.compute_analysis_key('i', 'p', 'b')
        self.assertRegex(key, r'^[0-9a-f]{64}$')
        self.assertNotEqual(key, ac.compute_analysis_key('i', 'p', 'c'))
        with mock.patch.object(ac, 'CACHE_FORMAT_VERSION', 'v2'):
            self.assertNotEqual(key, ac.compute_analysis_key('i', 'p', 'b'))


class SourceRootTest(unittest.TestCase):

    def test_whole_prefix_only(self):
        text = '/work/src/a.c /work/src2/b.c "/work/src" /work/src'
        self.assertEqual(
            ac.replace_source_root(text, '/work/src'),
            '__SOURCE_ROOT__/a.c /work/src2/b.c "__SOURCE_ROOT__" '
            '__SOURCE_ROOT__')

    def test_preprocessed_output(self):
        out = b'# 1 "/work/src/a.c"\n# 1 "/work/src/inc/h.h" 1\n'
        self.assertEqual(
            ac.replace_source_root_bytes(out, '/work/src'),
            b'# 1 "__SOURCE_ROOT__/a.c"\n# 1 "__SOURCE_ROOT__/inc/h.h" 1\n')

    def test_plist_roundtrip(self):
        plist = b'<string>/a&amp;b/src/f.c</string>' \
                b'<string>/a&amp;b/src2/g.c</string>'
        stored = ac.replace_source_root_in_plist(plist, '/a&b/src')
        self.assertEqual(stored, b'<string>__SOURCE_ROOT__/f.c</string>'
                                 b'<string>/a&amp;b/src2/g.c</string>')
        self.assertEqual(
            ac.restore_source_root_in_plist(stored, '/x&y'),
            b'<string>/x&amp;y/f.c</string>'
            b'<string>/a&amp;b/src2/g.c</string>')

    def test_normalize(self):
        self.assertEqual(ac.normalize_source_root('/work/src/'), '/work/src')
        self.assertTrue(os.path.isabs(ac.normalize_source_root('rel')))

    def test_preprocessed_source_key(self):
        d1, d2 = tempfile.mkdtemp(), tempfile.mkdtemp()
        try:
            for d in (d1, d2):
                with open(os.path.join(d, 'a.c'), 'w',
                          encoding='utf-8') as f:
                    f.write('int x;\n')
            k1 = ac.preprocessed_source_key(
                ['echo', '# 1 "' + d1 + '/a.c"'], d1, None, d1)
            k2 = ac.preprocessed_source_key(
                ['echo', '# 1 "' + d2 + '/a.c"'], d2, None, d2)
            self.assertEqual(k1, k2)
            self.assertIsNone(
                ac.preprocessed_source_key(['false'], d1, None, d1))
            self.assertIsNone(
                ac.preprocessed_source_key(['/nonexistent/x'], d1, None,
                                           d1))
        finally:
            shutil.rmtree(d1)
            shutil.rmtree(d2)


class ContentTest(unittest.TestCase):

    def test_roundtrip(self):
        self.assertEqual(ac.decode_content(ac.encode_content(b'abc')),
                         b'abc')

    def test_zip_bomb(self):
        bomb = base64.b64encode(zlib.compress(b'\0' * (5 * 1024 * 1024)))
        with self.assertRaises(ac.CacheContentError):
            ac.decode_content(bomb.decode(), max_size=1024 * 1024)

    def test_invalid(self):
        for content in ['!!!', base64.b64encode(b'not zlib').decode(),
                        base64.b64encode(zlib.compress(b'x' * 100)[:-4])
                        .decode()]:
            with self.assertRaises(ac.CacheContentError):
                ac.decode_content(content)


class SafeWriteTest(unittest.TestCase):

    def setUp(self):
        self.report_dir = tempfile.mkdtemp()
        self.outside = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.report_dir)
        shutil.rmtree(self.outside)

    def test_write_inside(self):
        target = os.path.join(self.report_dir, 'r.plist')
        self.assertTrue(ac.safe_write_file(self.report_dir, target, b'x'))
        with open(target, 'rb') as f:
            self.assertEqual(f.read(), b'x')
        self.assertEqual(os.listdir(self.report_dir), ['r.plist'])

    def test_target_outside(self):
        target = os.path.join(self.outside, 'r.plist')
        self.assertFalse(ac.safe_write_file(self.report_dir, target, b'x'))
        self.assertFalse(os.path.exists(target))

        traversal = os.path.join(self.report_dir, '..',
                                 os.path.basename(self.outside), 'r.plist')
        self.assertFalse(ac.safe_write_file(self.report_dir, traversal,
                                            b'x'))

    def test_symlink_target_not_followed(self):
        victim = os.path.join(self.outside, 'victim')
        link = os.path.join(self.report_dir, 'r.plist')
        os.symlink(victim, link)
        self.assertTrue(ac.safe_write_file(self.report_dir, link, b'x'))
        self.assertFalse(os.path.islink(link))
        self.assertFalse(os.path.exists(victim))

    def test_symlinked_parent_dir(self):
        link_dir = os.path.join(self.report_dir, 'sub')
        os.symlink(self.outside, link_dir)
        self.assertFalse(ac.safe_write_file(
            self.report_dir, os.path.join(link_dir, 'r.plist'), b'x'))
        self.assertEqual(os.listdir(self.outside), [])


class CacheSessionTest(unittest.TestCase):

    def test_write_read_roundtrip(self):
        client = FakeClient()
        writer = session_with(client, source_root='/work/src')
        plist = b'<string>/work/src/a.c</string>'
        self.assertTrue(writer.write('k', plist, 'out', 'err'))

        stored = dict(client.store['k'])
        self.assertEqual(set(stored), set(ac.ROLES))
        self.assertIn(b'__SOURCE_ROOT__',
                      ac.decode_content(stored[ac.ROLE_RESULT]))

        reader = session_with(client, source_root='/home/u/co')
        entry = reader.read('k')
        self.assertEqual(entry.result, b'<string>/home/u/co/a.c</string>')
        self.assertEqual((entry.stdout, entry.stderr), ('out', 'err'))

    def test_miss_and_role_filtering(self):
        client = FakeClient()
        session = session_with(client)
        self.assertIsNone(session.read('k'))

        client.store['k'] = [('evil.sh', ac.encode_content(b'x'))]
        self.assertIsNone(session.read('k'))

        client.store['k'] = [('evil.sh', ac.encode_content(b'x')),
                             (ac.ROLE_RESULT, ac.encode_content(b'r'))]
        self.assertEqual(session.read('k').result, b'r')

    def test_invalid_content_is_miss(self):
        client = FakeClient()
        client.store['k'] = [(ac.ROLE_RESULT, '!!!')]
        self.assertIsNone(session_with(client).read('k'))

    def test_too_large_not_written(self):
        client = FakeClient()
        session = session_with(client)
        with mock.patch.object(ac, 'MAX_FILE_SIZE', 10), \
                self.assertLogs('analyzer', level='WARNING') as logs:
            self.assertFalse(session.write('k', b'x' * 11, '', '', 'a.c'))
        self.assertEqual(client.writes, 0)
        self.assertIn('too large for the analysis cache', logs.output[0])

    def test_fail_open(self):
        client = FakeClient()
        client.fail = True
        session = session_with(client)
        for _ in range(ac.MAX_CONSECUTIVE_ERRORS):
            self.assertIsNone(session.read('k'))
        self.assertTrue(session.disabled)
        # Disabled sessions do not call the server anymore.
        client.fail = False
        client.store['k'] = [(ac.ROLE_RESULT, ac.encode_content(b'r'))]
        self.assertIsNone(session.read('k'))
        self.assertFalse(session.write('k', b'r', '', ''))

    def test_error_counter_reset(self):
        client = FakeClient()
        session = session_with(client)
        client.fail = True
        session.read('k')
        session.read('k')
        client.fail = False
        session.read('k')
        client.fail = True
        session.read('k')
        session.read('k')
        self.assertFalse(session.disabled)
