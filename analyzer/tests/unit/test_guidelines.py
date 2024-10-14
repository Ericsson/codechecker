# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Tests for Guidelines class."""


import yaml
import os
import tempfile
import unittest

from codechecker_common.guidelines import Guidelines


class TestGuidelines(unittest.TestCase):
    def setUp(self) -> None:
        self.guidelines_dir = tempfile.TemporaryDirectory()
        self.initialize_guidelines_dir()

    def tearDown(self) -> None:
        self.guidelines_dir.cleanup()

    def initialize_guidelines_dir(self):
        guidelines = {
            "guideline": "sei-cert",
            "guideline_title": "SEI CERT Coding Standard",
            "rules": [
                {
                    "rule_id": "con50-cpp",
                    "rule_url": "https://wiki.sei.cmu.edu/confluence/display"
                                "/cplusplus/CON50-CPP.+Do+not+destroy+a+mutex"
                                "+while+it+is+locked",
                    "rule_title": ""
                },
                {
                    "rule_id": "con51-cpp",
                    "rule_url": "https://wiki.sei.cmu.edu/confluence/display"
                                "/cplusplus/CON51-CPP.+Ensure+actively+held+"
                                "locks+are+released+on+exceptional+conditions",
                    "rule_title": ""
                },
                {
                    "rule_id": "con52-cpp",
                    "rule_url": "https://wiki.sei.cmu.edu/confluence/display"
                                "/cplusplus/CON52-CPP.+Prevent+data+races+when"
                                "+accessing+bit-fields+from+multiple+threads",
                    "rule_title": ""
                },
                {
                    "rule_id": "con53-cpp",
                    "rule_url": "https://wiki.sei.cmu.edu/confluence/display"
                                "/cplusplus/CON53-CPP.+Avoid+deadlock+by+"
                                "locking+in+a+predefined+order",
                    "rule_title": ""
                },
            ]
        }

        with open(os.path.join(self.guidelines_dir.name, 'sei-cert.yaml'),
                  'w', encoding='utf-8') as fp:
            yaml.safe_dump(guidelines, fp, default_flow_style=False)

    def test_guidelines(self):
        g = Guidelines(self.guidelines_dir.name)

        self.assertNotEqual(len(g.rules_of_guideline("sei-cert")), 0)

        self.assertEqual(
            sorted(g.rules_of_guideline("sei-cert").keys()),
            ["con50-cpp", "con51-cpp", "con52-cpp", "con53-cpp"])

        self.assertEqual(
            g.rules_of_guideline("sei-cert"),
            {
                "con50-cpp": {
                    "rule_url": "https://wiki.sei.cmu.edu/confluence/display"
                                "/cplusplus/CON50-CPP.+Do+not+destroy+a+mutex"
                                "+while+it+is+locked",
                    "rule_title": ""
                },
                "con51-cpp": {
                    "rule_url": "https://wiki.sei.cmu.edu/confluence/display"
                                "/cplusplus/CON51-CPP.+Ensure+actively+held+"
                                "locks+are+released+on+exceptional+conditions",
                    "rule_title": ""
                },
                "con52-cpp": {
                    "rule_url": "https://wiki.sei.cmu.edu/confluence/display"
                                "/cplusplus/CON52-CPP.+Prevent+data+races+when"
                                "+accessing+bit-fields+from+multiple+threads",
                    "rule_title": ""
                },
                "con53-cpp": {
                    "rule_url": "https://wiki.sei.cmu.edu/confluence/display"
                                "/cplusplus/CON53-CPP.+Avoid+deadlock+by+"
                                "locking+in+a+predefined+order",
                    "rule_title": ""
                },
            })
