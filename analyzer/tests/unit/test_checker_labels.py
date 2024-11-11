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
          "guideline": {
              "sei-cert": "SEI-CERT documentation"
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
                    "profile:default",
                    "profile:sensitive",
                    "severity:HIGH"
                ],
                "core.NonNullParamChecker": [
                    "profile:default",
                    "profile:sensitive",
                    "severity:HIGH"
                ],
                "core.builtin.NoReturnFunctions": [
                    "profile:default",
                    "profile:sensitive",
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
                    "profile:default",
                    "profile:sensitive",
                    "profile:extreme",
                    "severity:MEDIUM"
                ],
                "google-objc-global-variable-declaration": [
                    "profile:extreme"
                ],
                "cert-err34-c": [
                    "profile:sensitive",
                    "profile:security",
                    "profile:extreme",
                    "guideline:sei-cert",
                    "sei-cert:err34-c",
                    "severity:LOW"
                ]
            }
        }

        with open(os.path.join(self.labels_dir.name,
                               'analyzers',
                               'clang-tidy.json'), 'w', encoding='utf-8') as f:
            json.dump(labels, f)

    def test_checker_labels(self):
        cl = CheckerLabels(self.labels_dir.name)

        self.assertEqual(
            sorted(cl.get_analyzers()),
            sorted([
                "clang-tidy",
                "clangsa"
            ]))

        self.assertEqual(
            sorted(cl.checkers_by_labels([
                'profile:extreme'])),
            sorted([
                'core.builtin.NoReturnFunctions',
                'bugprone-undelegated-constructor',
                'google-objc-global-variable-declaration',
                'cert-err34-c']))

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
            sorted(cl.labels()),
            sorted(['guideline', 'profile', 'sei-cert', 'severity']))

        self.assertEqual(
            sorted(cl.occurring_values('profile')),
            sorted(['default', 'extreme', 'security', 'sensitive']))

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
