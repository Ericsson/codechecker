# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Functional tests of the server-side analysis cache.
"""

import json
import os
import shutil
import subprocess
import unittest

import multiprocess

from codechecker_api.python.shared.ttypes import Permission, RequestFailed, \
    ErrorCode
from codechecker_client.analysis_cache_client import AnalysisCacheClient

from codechecker_common.util import load_json

from libtest import codechecker
from libtest import env
from libtest.mock_bazel_remote import MockBazelRemote


PRODUCT = 'analysis_cache'
OTHER_PRODUCT = 'analysis_cache_other'

# 'john' may use the cache, 'cc' (PRODUCT_STORE) and 'admin'
# (PRODUCT_ADMIN) may not: PRODUCT_CACHE is not inherited.
USER_PERMISSIONS = [("cc", Permission.PRODUCT_STORE),
                    ("john", Permission.PRODUCT_CACHE),
                    ("admin", Permission.PRODUCT_ADMIN)]

KEY = 'b' * 64

SOURCES = {
    'a.c': 'int f(int *p) { if (!p) return *p; return 0; }\n'
           'int g(int x) { return 10 / (x - x); }\n',
    'b.c': '#include "inc/b.h"\n'
           'int h(void) { int *q = 0; return *q + B; }\n',
    'inc/b.h': '#define B 1\n',
}


def create_checkout(path):
    """ Create a test project checkout with a compilation database. """
    src = os.path.join(path, 'src')
    for name, content in SOURCES.items():
        file_path = os.path.join(src, name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    compile_commands = [{'directory': src, 'file': name,
                         'command': f'gcc -c {name}'}
                        for name in ('a.c', 'b.c')]
    with open(os.path.join(path, 'compile_commands.json'), 'w',
              encoding='utf-8') as f:
        json.dump(compile_commands, f)


class TestAnalysisCache(unittest.TestCase):

    def setup_class(self):
        global EVENT, MOCK, TEST_WORKSPACE

        EVENT = multiprocess.Event()
        MOCK = MockBazelRemote().start()

        TEST_WORKSPACE = env.get_workspace('analysis_cache')
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        codechecker_cfg = {
            'check_env': env.test_env(TEST_WORKSPACE),
            'workspace': TEST_WORKSPACE,
            'checkers': [],
            'viewer_host': 'localhost',
            'viewer_port': env.get_free_port(),
            'viewer_product': PRODUCT,
            'analyzers': ['clangsa'],
        }
        env.export_test_cfg(TEST_WORKSPACE,
                            {'codechecker_cfg': codechecker_cfg})

        # Authentication enabled server which uses the mock backend.
        env.enable_auth(TEST_WORKSPACE)
        cfg_file = os.path.join(TEST_WORKSPACE, 'server_config.json')
        server_cfg = load_json(cfg_file)
        server_cfg['analysis_cache'] = {'url': MOCK.url, 'timeout': 10}
        with open(cfg_file, 'w', encoding='utf-8') as f:
            json.dump(server_cfg, f, indent=2)

        server_access = codechecker.start_server(codechecker_cfg, EVENT)
        for product in (PRODUCT, OTHER_PRODUCT):
            server_access['viewer_product'] = product
            codechecker.add_test_package_product(
                server_access, TEST_WORKSPACE,
                user_permissions=USER_PERMISSIONS,
                database_name=product)

        # Run the analyses as 'john' (PRODUCT_CACHE).
        codechecker.login(codechecker_cfg, TEST_WORKSPACE, 'john', 'doe')

    def teardown_class(self):
        check_env = env.import_test_cfg(TEST_WORKSPACE)[
            'codechecker_cfg']['check_env']
        codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)
        EVENT.set()
        MOCK.stop()
        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, _):
        self._cfg = env.import_codechecker_cfg(TEST_WORKSPACE)
        self._host = self._cfg['viewer_host']
        self._port = self._cfg['viewer_port']
        self._url = f"http://{self._host}:{self._port}/{PRODUCT}"
        self._auth_client = env.setup_auth_client(TEST_WORKSPACE,
                                                  session_token='_PROHIBIT')
        MOCK.fail_status = None
        MOCK.cas.clear()
        MOCK.ac.clear()

    def __api(self, user, password, product=PRODUCT):
        token = self._auth_client.performLogin("Username:Password",
                                               f"{user}:{password}")
        return AnalysisCacheClient('http', self._host, self._port, product,
                                   token)

    def __analyze(self, checkout, report_dir, extra_args=None):
        cmd = [env.codechecker_cmd(), 'analyze',
               os.path.join(checkout, 'compile_commands.json'),
               '-o', report_dir, '--analyzers', 'clangsa',
               '--url', self._url, '--source-root', checkout]
        cmd += extra_args or []
        proc = subprocess.run(cmd, cwd=checkout, env=self._cfg['check_env'],
                              capture_output=True, text=True,
                              encoding='utf-8', errors='ignore',
                              check=False)
        print(proc.stdout)
        print(proc.stderr)
        return proc.returncode, proc.stdout + proc.stderr

    def __parse(self, report_dir):
        proc = subprocess.run(
            [env.codechecker_cmd(), 'parse', report_dir],
            env=self._cfg['check_env'], capture_output=True, text=True,
            encoding='utf-8', errors='ignore', check=False)
        return sorted(line for line in proc.stdout.splitlines()
                      if line.startswith('[') and '] /' in line)

    # --- API level tests -------------------------------------------------

    def test_permission(self):
        """ Only the users with PRODUCT_CACHE may use the cache. """
        contents = [('result.plist', 'eJwrzs9JLUnNKy4BAA9pA78=')]
        john = self.__api('john', 'doe')
        john.write_cache(KEY, contents)
        self.assertEqual(john.read_cache(KEY), contents)

        for user, password in [('cc', 'test'), ('admin', 'admin123')]:
            client = self.__api(user, password)
            with self.assertRaises(RequestFailed) as ctx:
                client.read_cache(KEY)
            self.assertEqual(ctx.exception.errorCode,
                             ErrorCode.UNAUTHORIZED)
            with self.assertRaises(RequestFailed):
                client.write_cache(KEY, contents)

        # SUPERUSER inherits every permission.
        self.assertEqual(self.__api('root', 'root').read_cache(KEY),
                         contents)

    def test_product_isolation(self):
        contents = [('result.plist', 'eJwrzs9JLUnNKy4BAA9pA78=')]
        self.__api('john', 'doe').write_cache(KEY, contents)
        self.assertEqual(
            self.__api('john', 'doe', OTHER_PRODUCT).read_cache(KEY), [])

    def test_invalid_input(self):
        john = self.__api('john', 'doe')
        with self.assertRaises(RequestFailed) as ctx:
            john.write_cache(KEY, [('../evil', 'eJwDAAAAAAE=')])
        self.assertEqual(ctx.exception.errorCode, ErrorCode.GENERAL)
        with self.assertRaises(RequestFailed):
            john.read_cache('not-a-key')
        self.assertEqual(MOCK.cas, {})

    def test_backend_unavailable(self):
        MOCK.fail_status = 503
        with self.assertRaises(RequestFailed) as ctx:
            self.__api('john', 'doe').read_cache(KEY)
        self.assertEqual(ctx.exception.errorCode, ErrorCode.IOERROR)

    # --- End to end tests ------------------------------------------------

    def test_end_to_end_location_independent(self):
        """
        The first run fills the cache, the second run (in another checkout
        directory) fetches every action from the cache, and its reports
        refer to the files of the second checkout.
        """
        co1 = os.path.join(TEST_WORKSPACE, 'checkout1')
        co2 = os.path.join(TEST_WORKSPACE, 'checkout2')
        create_checkout(co1)
        create_checkout(co2)

        ret, out = self.__analyze(co1, os.path.join(co1, 'reports'))
        self.assertEqual(ret, 0)
        self.assertIn("Fetched from analysis cache: 0 / 2", out)
        self.assertEqual(len(MOCK.ac), 2)

        ret, out = self.__analyze(co2, os.path.join(co2, 'reports'))
        self.assertEqual(ret, 0)
        self.assertIn("Fetched from analysis cache: 2 / 2", out)

        reports1 = self.__parse(os.path.join(co1, 'reports'))
        reports2 = self.__parse(os.path.join(co2, 'reports'))
        self.assertEqual(len(reports1), 3)
        self.assertEqual([r.replace(co1, co2) for r in reports1], reports2)
        self.assertTrue(all(co1 not in r for r in reports2))

        # Post-processing settings which are not part of the key are applied
        # to the cached raw result of the current run.
        ret, out = self.__analyze(co2, os.path.join(co2, 'reports_hash'),
                                  ['--report-hash', 'context-free-v2'])
        self.assertIn("Fetched from analysis cache: 2 / 2", out)
        self.assertEqual(
            len(self.__parse(os.path.join(co2, 'reports_hash'))), 3)

        # A different checker set changes the analyzer command, so it is a
        # cache miss.
        ret, out = self.__analyze(co2, os.path.join(co2, 'reports_dis'),
                                  ['--disable', 'core.DivideZero'])
        self.assertIn("Fetched from analysis cache: 0 / 2", out)
        reports3 = self.__parse(os.path.join(co2, 'reports_dis'))
        self.assertEqual(len(reports3), 2)
        self.assertTrue(all('DivideZero' not in r for r in reports3))

    def test_source_change_is_miss(self):
        co = os.path.join(TEST_WORKSPACE, 'checkout_change')
        create_checkout(co)
        self.__analyze(co, os.path.join(co, 'reports'))

        with open(os.path.join(co, 'src', 'inc', 'b.h'), 'w',
                  encoding='utf-8') as f:
            f.write('#define B 2\n')
        _, out = self.__analyze(co, os.path.join(co, 'reports'))
        self.assertIn("Fetched from analysis cache: 1 / 2", out)

    def test_no_cache(self):
        co = os.path.join(TEST_WORKSPACE, 'checkout_nocache')
        create_checkout(co)
        requests_before = len(MOCK.requests)
        ret, out = self.__analyze(co, os.path.join(co, 'reports'),
                                  ['--no-cache'])
        self.assertEqual(ret, 0)
        self.assertNotIn("analysis cache", out)
        self.assertEqual(len(MOCK.requests), requests_before)
        self.assertEqual(MOCK.ac, {})

    def test_backend_unavailable_analysis_succeeds(self):
        co = os.path.join(TEST_WORKSPACE, 'checkout_down')
        create_checkout(co)
        MOCK.fail_status = 503
        ret, out = self.__analyze(co, os.path.join(co, 'reports'))
        self.assertEqual(ret, 0)
        self.assertIn("Fetched from analysis cache: 0 / 2", out)
        self.assertEqual(len(self.__parse(os.path.join(co, 'reports'))), 3)

    def test_source_root_mandatory(self):
        co = os.path.join(TEST_WORKSPACE, 'checkout_noroot')
        create_checkout(co)
        proc = subprocess.run(
            [env.codechecker_cmd(), 'analyze',
             os.path.join(co, 'compile_commands.json'),
             '-o', os.path.join(co, 'reports'), '--url', self._url],
            env=self._cfg['check_env'], capture_output=True, text=True,
            check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("'--source-root' is mandatory",
                      proc.stdout + proc.stderr)
