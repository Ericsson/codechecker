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

from codechecker_common.guidelines import Guidelines, Rule


class TestGuidelines(unittest.TestCase):
    def setUp(self) -> None:
        # Guidelines derives the rules dir as a sibling of the guidelines dir.
        self.config_dir = tempfile.TemporaryDirectory()
        self.guidelines_dir = os.path.join(self.config_dir.name, 'guidelines')
        self.rules_dir = os.path.join(self.config_dir.name, 'rules')
        os.mkdir(self.guidelines_dir)
        os.mkdir(self.rules_dir)
        self.initialize_guidelines_dir()

    def tearDown(self) -> None:
        self.config_dir.cleanup()

    def initialize_guidelines_dir(self):
        base_url = ("https://cmu-sei.github.io/secure-coding-standards/"
                    "sei-cert-cpp-coding-standard/rules/concurrency-con")

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

        with open(os.path.join(self.rules_dir, 'sei-cert-rules.yaml'),
                  'w', encoding='utf-8') as fp:
            yaml.safe_dump(rules, fp, default_flow_style=False)

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

        with open(os.path.join(self.guidelines_dir, 'sei-cert-cpp.yaml'),
                  'w', encoding='utf-8') as fp:
            yaml.safe_dump(guidelines, fp, default_flow_style=False)

    def test_guidelines(self):
        g = Guidelines(self.guidelines_dir)

        self.assertNotEqual(len(g.rules_of_guideline("sei-cert-cpp")), 0)

        self.assertEqual(
            sorted(g.rules_of_guideline("sei-cert-cpp").keys()),
            ["con50-cpp", "con51-cpp", "con52-cpp", "con53-cpp"])

        base_url = ("https://cmu-sei.github.io/secure-coding-standards/"
                    "sei-cert-cpp-coding-standard/rules/concurrency-con")

        self.assertEqual(
            g.rules_of_guideline("sei-cert-cpp"),
            {
                "con50-cpp": Rule(
                    rule_id="con50-cpp",
                    title="",
                    rule_url=f"{base_url}/con50-cpp/"),
                "con51-cpp": Rule(
                    rule_id="con51-cpp",
                    title="",
                    rule_url=f"{base_url}/con51-cpp/"),
                "con52-cpp": Rule(
                    rule_id="con52-cpp",
                    title="",
                    rule_url=f"{base_url}/con52-cpp/"),
                "con53-cpp": Rule(
                    rule_id="con53-cpp",
                    title="",
                    rule_url=f"{base_url}/con53-cpp/"),
            })

    def test_guidelines_of_rule(self):
        g = Guidelines(self.guidelines_dir)

        self.assertEqual(
            g.guidelines_of_rule("con50-cpp"), ["sei-cert-cpp"])
        self.assertEqual(g.guidelines_of_rule("nonexistent"), [])

    def test_rule_details(self):
        g = Guidelines(self.guidelines_dir)

        base_url = ("https://cmu-sei.github.io/secure-coding-standards/"
                    "sei-cert-cpp-coding-standard/rules/concurrency-con")

        self.assertEqual(
            g.rule_details("con51-cpp"),
            Rule(
                rule_id="con51-cpp",
                title="",
                rule_url=f"{base_url}/con51-cpp/"))
        self.assertEqual(
            g.rule_details("nonexistent"),
            Rule(rule_id="nonexistent", title="", rule_url=""))
