# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Tests for CheckerLabels class."""


import json
import os
import tempfile
import unittest

from codechecker_common.checker_labels import CheckerLabels


class _FakeGuidelines:
    """
    Minimal stand-in for the Guidelines object. Maps rule ids to the
    guidelines that contain them.
    """
    def __init__(self, rule_to_guidelines):
        self._rule_to_guidelines = rule_to_guidelines

    def guidelines_of_rule(self, rule_id):
        return list(self._rule_to_guidelines.get(rule_id, []))


class TestCheckerLabels(unittest.TestCase):
    def setUp(self) -> None:
        self.labels_dir = tempfile.TemporaryDirectory()
        self.initialize_labels_dir()

    def tearDown(self) -> None:
        self.labels_dir.cleanup()

    def initialize_labels_dir(self):
        descriptions = {
          "profile": {
              "default": "Default documentation",
              "sensitive": "Sensitive documentation",
              "extreme": "Extreme documentation"
          },
          "severity": {
              "CRITICAL": "Critical documentation",
              "HIGH": "High documentation",
              "MEDIUM": "Medium documentation",
              "UNSPECIFIED": "Unspecified documentation"
          },
          "profile-containment": {
              "extreme": ["sensitive"],
              "sensitive": ["default"]
          }
        }

        with open(os.path.join(
                self.labels_dir.name, 'descriptions.json'),
                'w', encoding='utf-8') as f:
            json.dump(descriptions, f)

        os.mkdir(os.path.join(self.labels_dir.name, 'analyzers'))

        labels = {
            "analyzer": "clangsa",
            "labels": {
                "globalChecker": [
                    "profile:security",
                    "severity:HIGH"
                ],
                "core.DivideZero": [
                    "profile:sensitive",
                    "severity:HIGH"
                ],
                "core.NonNullParamChecker": [
                    "profile:sensitive",
                    "severity:HIGH"
                ],
                "core.builtin.NoReturnFunctions": [
                    "profile:extreme",
                    "severity:MEDIUM"
                ],
            }
        }

        with open(os.path.join(self.labels_dir.name,
                               'analyzers',
                               'clangsa.json'), 'w', encoding='utf-8') as f:
            json.dump(labels, f)

        labels = {
            "analyzer": "clang-tidy",
            "labels": {
                "globalChecker": [
                    "profile:security",
                    "severity:HIGH"
                ],
                "bugprone-undelegated-constructor": [
                    "profile:extreme",
                    "severity:MEDIUM"
                ],
                "google-objc-global-variable-declaration": [
                    "profile:extreme"
                ],
                "cert-err34-c": [
                    "profile:extreme",
                    "profile:security",
                    "rule:err34-c",
                    "severity:LOW"
                ]
            }
        }

        with open(os.path.join(self.labels_dir.name,
                               'analyzers',
                               'clang-tidy.json'), 'w', encoding='utf-8') as f:
            json.dump(labels, f)

    def test_checker_labels(self):
        guidelines = _FakeGuidelines({"err34-c": ["sei-cert-c"]})
        cl = CheckerLabels(self.labels_dir.name, guidelines)

        self.assertEqual(
            sorted(cl.get_analyzers()),
            sorted([
                "clang-tidy",
                "clangsa"
            ]))

        # Query "extreme" expands to {extreme, sensitive, default}, so it
        # matches every checker with any containment tier.
        self.assertEqual(
            sorted(cl.checkers_by_labels([
                'profile:extreme'])),
            sorted([
                'core.DivideZero',
                'core.NonNullParamChecker',
                'core.builtin.NoReturnFunctions',
                'bugprone-undelegated-constructor',
                'google-objc-global-variable-declaration',
                'cert-err34-c']))

        # Query "sensitive" expands to {sensitive, default}: extreme-labeled
        # checkers are NOT matched.
        self.assertEqual(
            sorted(cl.checkers_by_labels([
                'profile:sensitive'], 'clangsa')),
            sorted([
                'core.DivideZero',
                'core.NonNullParamChecker']))

        # Query "default" matches only default-labeled checkers (smallest
        # set). The test data has none in clangsa.
        self.assertEqual(
            sorted(cl.checkers_by_labels(['profile:default'], 'clangsa')),
            [])

        self.assertEqual(
            sorted(cl.checkers_by_labels([
                'profile:extreme',
                'severity:HIGH'])),
            sorted([
                'globalChecker',
                'globalChecker',
                'core.DivideZero',
                'core.NonNullParamChecker',
                'core.builtin.NoReturnFunctions',
                'bugprone-undelegated-constructor',
                'google-objc-global-variable-declaration',
                'cert-err34-c']))

        self.assertEqual(
            sorted(cl.checkers_by_labels([
                'profile:extreme',
                'severity:HIGH'], 'clangsa')),
            sorted([
                'globalChecker',
                'core.DivideZero',
                'core.NonNullParamChecker',
                'core.builtin.NoReturnFunctions']))

        self.assertEqual(
            cl.label_of_checker('globalChecker', 'severity'),
            'HIGH')

        self.assertEqual(
            cl.label_of_checker('globalChecker', 'profile'),
            ['security'])

        # label_of_checker returns the checker's single containment tier;
        # the containment relation is applied on the query side, not here.
        self.assertEqual(
            cl.label_of_checker(
                'core.builtin.NoReturnFunctions', 'profile', 'clangsa'),
            ['extreme'])

        # Guideline derived from the rule label.
        self.assertEqual(
            cl.label_of_checker('cert-err34-c', 'guideline', 'clang-tidy'),
            ['sei-cert-c'])

        self.assertEqual(
            cl.label_of_checker(
                'bugprone-undelegated-constructor', 'severity', 'clang-tidy'),
            'MEDIUM')

        self.assertEqual(
            cl.label_of_checker(
                'bugprone-undelegated-constructor', 'severity', 'clangsa'),
            'UNSPECIFIED')

        self.assertEqual(
            sorted(cl.labels_of_checker('globalChecker')),
            sorted([
                ('profile', 'security'),
                ('severity', 'HIGH')]))

        self.assertEqual(
            cl.severity('bugprone-undelegated-constructor'),
            'MEDIUM')

        self.assertEqual(
            cl.severity('bugprone-undelegated-constructor', 'clang-tidy'),
            'MEDIUM')

        self.assertEqual(
            cl.severity('bugprone-undelegated-constructor', 'clangsa'),
            'UNSPECIFIED')

        self.assertEqual(
            cl.get_description('profile'), {
                'default': 'Default documentation',
                'sensitive': 'Sensitive documentation',
                'extreme': 'Extreme documentation'})

        self.assertEqual(
            sorted(cl.checkers()),
            sorted([
                'globalChecker',
                'core.DivideZero',
                'core.NonNullParamChecker',
                'core.builtin.NoReturnFunctions',
                'globalChecker',
                'bugprone-undelegated-constructor',
                'google-objc-global-variable-declaration',
                'cert-err34-c']))

        self.assertEqual(
            sorted(cl.checkers('clang-tidy')),
            sorted([
                'globalChecker',
                'bugprone-undelegated-constructor',
                'google-objc-global-variable-declaration',
                'cert-err34-c']))
