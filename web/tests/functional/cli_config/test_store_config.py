#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test store configuration file.
"""


import json
import os
import subprocess
import unittest

from libtest import env

from . import setup_class_common, teardown_class_common


class TestStoreConfig(unittest.TestCase):
    _ccClient = None

    def setup_class(self):
        setup_class_common("store_config")

    def teardown_class(self):
        teardown_class_common()

    def setup_method(self, _):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']
        self.codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        self.config_file_json = os.path.join(
            self.test_workspace, "codechecker.json")
        self.config_file_yaml = os.path.join(
            self.test_workspace, "codechecker.yaml")

        # Create an empty report directory which will be used to check store
        # command.
        if not os.path.exists(self.codechecker_cfg['reportdir']):
            os.mkdir(self.codechecker_cfg['reportdir'])

    def test_valid_json_config(self):
        """ Store with a valid JSON configuration file. """
        cc_env = env.codechecker_env()
        cc_env["CC_REPORT_DIR"] = self.codechecker_cfg['reportdir']

        with open(self.config_file_json, 'w+',
                  encoding="utf-8", errors="ignore") as config_f:
            json.dump({
                'store': [
                    '--name=' + 'store_config',
                    '--trim-path-prefix=$HOME',
                    '--url=' + env.parts_to_url(self.codechecker_cfg),
                    '$CC_REPORT_DIR']}, config_f)

        store_cmd = [env.codechecker_cmd(), 'store', '--config',
                     self.config_file_json]

        try:
            subprocess.check_output(
                store_cmd, env=cc_env, encoding="utf-8", errors="ignore")
        except subprocess.CalledProcessError as cerr:
            print(cerr.output)
            raise

    def test_valid_yaml_config(self):
        """ Store with a valid YAML configuration file. """
        cc_env = env.codechecker_env()
        cc_env["CC_REPORT_DIR"] = self.codechecker_cfg['reportdir']

        with open(self.config_file_yaml, 'w+',
                  encoding="utf-8", errors="ignore") as config_f:
            config_f.write(f"""
# Storage related options.
store:
  - --name=store_config
  - --trim-path-prefix=$HOME
  - --url={env.parts_to_url(self.codechecker_cfg)}
  - $CC_REPORT_DIR""")

        store_cmd = [env.codechecker_cmd(), 'store', '--config',
                     self.config_file_yaml]

        try:
            subprocess.check_output(
                store_cmd, env=cc_env, encoding="utf-8", errors="ignore")
        except subprocess.CalledProcessError as cerr:
            print(cerr.output)
            raise

    def test_invalid_config(self):
        """ Store with an invalid configuration file. """
        with open(self.config_file_json, 'w+',
                  encoding="utf-8", errors="ignore") as config_f:
            json.dump({
                'store': ['--dummy-option']}, config_f)

        store_cmd = [env.codechecker_cmd(), 'store',
                     '--name', 'store_config',
                     '--config', self.config_file_json,
                     '--url', env.parts_to_url(self.codechecker_cfg),
                     self.codechecker_cfg['reportdir']]

        with self.assertRaises(subprocess.CalledProcessError):
            subprocess.check_output(
                store_cmd, encoding="utf-8", errors="ignore")

    def test_empty_config(self):
        """ Store with an empty configuration file. """
        with open(self.config_file_json, 'w+',
                  encoding="utf-8", errors="ignore") as config_f:
            config_f.write("")

        store_cmd = [env.codechecker_cmd(), 'store',
                     '--name', 'store_config',
                     '--config', self.config_file_json,
                     '--url', env.parts_to_url(self.codechecker_cfg),
                     self.codechecker_cfg['reportdir']]

        try:
            subprocess.check_output(
                store_cmd, encoding="utf-8", errors="ignore")
        except subprocess.CalledProcessError as cerr:
            print(cerr.output)
            raise
