# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import os
from typing import Any, DefaultDict, Dict, Iterable, List
from collections import defaultdict

import yaml


class Guidelines:
    def __init__(self, guidelines_dir: str):
        if not os.path.isdir(guidelines_dir):
            raise NotADirectoryError(
                f'{guidelines_dir} is not a directory.')

        guideline_yaml_files = map(
            lambda f: os.path.join(guidelines_dir, f),
            os.listdir(guidelines_dir))

        self.__all_rules = self.__union_guideline_files(guideline_yaml_files)

    def __union_guideline_files(
        self,
        guideline_files: Iterable[str]
    ) -> DefaultDict[str, List[Dict[str, str]]]:
        """
        This function creates a union object of the given guideline files. The
        resulting object maps guidelines to the collection of their rules.
        E.g.:
        {
            "guideline1": [
                {
                    "rule_id": ...
                    "rule_url": ...
                    "title": ...
                },
                {
                    ...
                }
            ],
            "guideline2": [
                ...
            ],
        }
        """
        all_rules = defaultdict(list)

        for guideline_file in guideline_files:
            with open(guideline_file, "r", encoding="utf-8") as gf:
                guideline_data = yaml.safe_load(gf)

                guideline_name = guideline_data.get("guideline")
                rules = guideline_data.get("rules")

                all_rules[guideline_name].extend(rules)

        return all_rules

    def rules_of_guideline(
        self,
        guideline_name: str,
    ) -> List[Any]:
        """
        Return the list of rules of a guideline.
        """

        guideline_rules = self.__all_rules.get(guideline_name, [])

        return guideline_rules

    def all_guideline_rules(self) -> DefaultDict[str, List[Dict[str, str]]]:
        return self.__all_rules
