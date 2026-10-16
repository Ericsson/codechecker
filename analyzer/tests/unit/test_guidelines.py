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
        self.rules_dir = tempfile.TemporaryDirectory()
        self.initialize_guidelines_dir()

    def tearDown(self) -> None:
        self.guidelines_dir.cleanup()
        self.rules_dir.cleanup()

    def initialize_guidelines_dir(self):
        base_url = ("https://cmu-sei.github.io/secure-coding-standards/"
                    "sei-cert-cpp-coding-standard/rules/concurrency-con")

        # Rule details are the single source of truth (config/rules).
        rules = [
            {
                "rule_id": "con50-cpp",
                "title": "",
                "rule_url": f"{base_url}/con50-cpp/"
            },
            {
                "rule_id": "con51-cpp",
                "title": "",
                "rule_url": f"{base_url}/con51-cpp/"
            },
            {
                "rule_id": "con52-cpp",
                "title": "",
                "rule_url": f"{base_url}/con52-cpp/"
            },
            {
                "rule_id": "con53-cpp",
                "title": "",
                "rule_url": f"{base_url}/con53-cpp/"
            },
        ]

        with open(os.path.join(self.rules_dir.name, 'sei-cert-rules.yaml'),
                  'w', encoding='utf-8') as fp:
            yaml.safe_dump(rules, fp, default_flow_style=False)

        # Guideline descriptor references rule ids only (config/guidelines).
        guidelines = {
            "guideline": "sei-cert-cpp",
            "guideline_title": "SEI CERT C++ Coding Standard",
            "guideline_url":
                "https://cmu-sei.github.io/secure-coding-standards/"
                "sei-cert-cpp-coding-standard/",
            "rules": [
                {"rule_id": "con50-cpp"},
                {"rule_id": "con51-cpp"},
                {"rule_id": "con52-cpp"},
                {"rule_id": "con53-cpp"},
            ]
        }

        with open(os.path.join(self.guidelines_dir.name, 'sei-cert-cpp.yaml'),
                  'w', encoding='utf-8') as fp:
            yaml.safe_dump(guidelines, fp, default_flow_style=False)

    def test_guidelines(self):
        g = Guidelines(self.guidelines_dir.name, self.rules_dir.name)

        self.assertNotEqual(len(g.rules_of_guideline("sei-cert-cpp")), 0)

        self.assertEqual(
            sorted(g.rules_of_guideline("sei-cert-cpp").keys()),
            ["con50-cpp", "con51-cpp", "con52-cpp", "con53-cpp"])

        base_url = ("https://cmu-sei.github.io/secure-coding-standards/"
                    "sei-cert-cpp-coding-standard/rules/concurrency-con")

        self.assertEqual(
            g.rules_of_guideline("sei-cert-cpp"),
            {
                "con50-cpp": {
                    "rule_url": f"{base_url}/con50-cpp/",
                    "title": ""
                },
                "con51-cpp": {
                    "rule_url": f"{base_url}/con51-cpp/",
                    "title": ""
                },
                "con52-cpp": {
                    "rule_url": f"{base_url}/con52-cpp/",
                    "title": ""
                },
                "con53-cpp": {
                    "rule_url": f"{base_url}/con53-cpp/",
                    "title": ""
                },
            })

    def test_guidelines_of_rule(self):
        g = Guidelines(self.guidelines_dir.name, self.rules_dir.name)

        self.assertEqual(
            g.guidelines_of_rule("con50-cpp"), ["sei-cert-cpp"])
        self.assertEqual(g.guidelines_of_rule("nonexistent"), [])

    def test_rule_details(self):
        g = Guidelines(self.guidelines_dir.name, self.rules_dir.name)

        base_url = ("https://cmu-sei.github.io/secure-coding-standards/"
                    "sei-cert-cpp-coding-standard/rules/concurrency-con")

        self.assertEqual(
            g.rule_details("con51-cpp"),
            {"title": "", "rule_url": f"{base_url}/con51-cpp/"})
        self.assertEqual(
            g.rule_details("nonexistent"),
            {"title": "", "rule_url": ""})
