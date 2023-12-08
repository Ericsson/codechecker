# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""TODO"""


import os
import unittest

from codechecker_common.review_status_handler import ReviewStatusHandler
from libtest import env


class ReviewStatusHandlerTest(unittest.TestCase):
    """
    Test the build command escaping and execution.
    """

    @classmethod
    def setup_class(self):
        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('review_status_config')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE
        self._test_workspace = os.environ['TEST_WORKSPACE']

    @classmethod
    def teardown_class(self):
        pass

    def setup_method(self, method):
        self.rshandler = ReviewStatusHandler(None)
        pass

    def teardown_method(self, method):
        pass

    def __put_in_review_status_cfg_file(self, file_contents: str) -> str:
        rs_cfg = os.path.join(self._test_workspace, "review_status.yaml")
        with open(rs_cfg, "w") as f:
            f.write(file_contents)

        return rs_cfg

    def test_empty_file(self):
        cfg = ""
        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(
                ValueError, "should represent a dictionary."):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_no_version(self):
        cfg = """
rules:
  - filters:
      checker_name: core.NullDereference
    actions:
      review_status: intentional
      reason: Division by zero in test files is automatically intentional.
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(
                ValueError, r"must contain the key '\$version'"):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_empty_action_list(self):
        cfg = """
$version: 1
rules:
  - filters:
      checker_name: core.NullDereference
    actions:
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(
                ValueError, "'actions' must have at least one element"):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_empty_filter_list(self):
        cfg = """
$version: 1
rules:
  - filters:
    actions:
      review_status: intentional
      reason: Division by zero in test files is automatically intentional.
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(
                ValueError, "'filters' must have at least one element."):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_empty_filter_and_action_list(self):
        cfg = """
$version: 1
rules:
  - filters:
    actions:
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(
                ValueError, "'filters' must have at least one element."):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_empty_rules_list(self):
        cfg = """
$version: 1
rules:
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(
                ValueError,
                "should contain the key 'rules' with a non-empty list of"):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_correct(self):
        cfg = """
$version: 1
rules:
  - filters:
      checker_name: core.NullDereference
    actions:
      review_status: intentional
      reason: Division by zero in test files is automatically intentional.
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        self.rshandler.set_review_status_config(rscfg_file)

    def test_invalid_review_status(self):
        cfg = """
$version: 1
rules:
  - filters:
      checker_name: core.NullDereference
    actions:
      review_status: oopsie
      reason: Division by zero in test files is automatically intentional.
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(
                ValueError, "Invalid review status field: "):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_invalid_action(self):
        cfg = """
$version: 1
rules:
  - filters:
      checker_name: core.NullDereference
    actions:
        bake: cake
        reason: Birthday
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(
                ValueError, "'bake' is not allowed"):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_no_review_status(self):
        cfg = """
$version: 1
rules:
  - filters:
      checker_name: core.NullDereference
    actions:
        reason: Birthday
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(
                ValueError, "review_status' .* required"):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_invalid_filter(self):
        cfg = """
$version: 1
rules:
  - filters:
      favourite_color: green
    actions:
      review_status: intentional
      reason: Division by zero in test files is automatically intentional.
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(
                ValueError, "'favourite_color' is not allowed"):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_no_actions(self):
        cfg = """
$version: 1
rules:
  - filters:
      checker_name: core.NullDereference
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(ValueError, "'filters' and 'actions'"):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_no_filters(self):
        cfg = """
$version: 1
rules:
  - actions:
      review_status: intentional
      reason: Division by zero in test files is automatically intentional.
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(ValueError, "'filters' and 'actions'"):
            self.rshandler.set_review_status_config(rscfg_file)

    # TODO: The "reason" field is not required. It is also not required for
    # review statuses with source code comment.
    def no_reason(self):
        cfg = """
$version: 1
rules:
  - filters:
      checker_name: core.NullDereference
    actions:
      review_status: intentional
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(ValueError, "TODO"):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_no_rules(self):
        cfg = """
$version: 1
  - filters:
      checker_name: core.NullDereference
    actions:
      review_status: intentional
      reason: Division by zero in test files is automatically intentional.
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(ValueError, "Invalid YAML"):
            self.rshandler.set_review_status_config(rscfg_file)

    def test_no_rules2(self):
        cfg = """
$version: 1
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(
                ValueError,
                "should contain the key 'rules' with a non-empty list of"):
            self.rshandler.set_review_status_config(rscfg_file)

    # TODO: I'm not sure if we can check this. The yaml parser accepts this and
    # later there is no opportunity to check double keys because we have a
    # valid Python object only.
    def multiple_checker_keys(self):
        cfg = """
$version: 1
rules:
  - filters:
      checker_name: core.NullDereference
      checker_name: core.DivByZero
    actions:
      review_status: intentional
      review_status: suppress
      reason: Division by zero in test files is automatically intentional.
        """

        rscfg_file = self.__put_in_review_status_cfg_file(cfg)
        with self.assertRaisesRegex(ValueError, "TODO"):
            self.rshandler.set_review_status_config(rscfg_file)
