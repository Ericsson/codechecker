# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import os
from typing import DefaultDict, Dict, Iterable
from collections import defaultdict

from codechecker_common.util import load_yaml
from codechecker_common.logger import get_logger

LOG = get_logger('system')


class Guidelines:
    def __init__(self, guidelines_dir: str):
        if not os.path.isdir(guidelines_dir):
            raise NotADirectoryError(
                f'{guidelines_dir} is not a directory.')

        guideline_yaml_files = map(
            lambda f: os.path.join(guidelines_dir, f),
            filter(lambda f: not f.endswith('.license'),
                   os.listdir(guidelines_dir)))

        self.__all_rules = self.__union_guideline_files(guideline_yaml_files)

    def __check_guideline_format(self, guideline_data: dict):
        """
        Check the format of a guideline, It must contain specific values with
        specific types. In case of any format error a ValueError exception is
        thrown with the description of the wrong format.
        """

        if "guideline" not in guideline_data \
           or not isinstance(guideline_data["guideline"], str):
            raise ValueError(
                "The 'guideline' field must exist and be a string.")

        if "guideline_title" not in guideline_data \
           or not isinstance(guideline_data["guideline_title"], str):
            raise ValueError(
                "The 'guideline_title' field must exist and be a string.")

        rules = guideline_data.get("rules")
        if not isinstance(rules, list) \
           or not all(map(lambda r: isinstance(r, dict), rules)):
            raise ValueError(
                "The 'rules' field must exist and be a list of dictionaris.")

        if any(map(lambda rule: "rule_id" not in rule
           or not isinstance(rule["rule_id"], str), rules)):
            raise ValueError(
                "All rules must have 'rule_id' that is a string.")

    def __union_guideline_files(
        self,
        guideline_files: Iterable[str]
    ) -> DefaultDict[str, Dict[str, Dict[str, str]]]:
        """
        This function creates a union object of the given guideline files. The
        resulting object maps guidelines to the collection of their rules.
        E.g.:
        {
            "guideline1": {
                "rule_id1": {
                    "rule_url": ...
                    "title": ...
                },
                "rule_id2": {
                    ...
                }
            ],
            "guideline2": {
                ...
            },
        }
        """
        all_rules: DefaultDict[
            str, Dict[str, Dict[str, str]]] = defaultdict(dict)

        for guideline_file in guideline_files:
            guideline_data = load_yaml(guideline_file)

            try:
                self.__check_guideline_format(guideline_data)

                guideline_name = guideline_data["guideline"]
                rules = guideline_data["rules"]
                all_rules[guideline_name] = {rule.pop("rule_id"): rule
                                             for rule in rules}
            except ValueError as ex:
                LOG.warning("%s does not have a correct guideline format.",
                            guideline_file)
                LOG.warning(ex)

        return all_rules

    def rules_of_guideline(
        self,
        guideline_name: str,
    ) -> Dict[str, Dict[str, str]]:
        """
        Return the list of rules of a guideline.
        """

        guideline_rules = self.__all_rules[guideline_name]

        return guideline_rules

    def all_guideline_rules(
        self
    ) -> DefaultDict[str, Dict[str, Dict[str, str]]]:
        return self.__all_rules
