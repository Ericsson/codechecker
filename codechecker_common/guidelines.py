# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import os
from typing import Iterable, List, Optional
from collections import defaultdict

from codechecker_common.util import load_yaml
from codechecker_common.logger import get_logger

LOG = get_logger('system')


class Guidelines:
    """
    Represents the guideline and rule descriptors.

    A guideline (e.g. "sei-cert-c") is a named grouping of rule ids. Guideline
    descriptors live in the guidelines directory and only reference rule ids.
    The detailed information of a rule (title, url) is stored separately in the
    rules directory (one file per rule type, e.g. "cwe-rules.yaml") which is
    the single source of truth for rule details.

    This class joins the two sources so that:
      - guideline membership comes from the guideline descriptors,
      - rule details (title, url) come from the rules descriptors,
    and provides a reverse lookup from a rule id to the guidelines that
    contain it.
    """

    def __init__(
        self,
        guidelines_dir: str,
        rules_dir: Optional[str] = None
    ):
        if not os.path.isdir(guidelines_dir):
            raise NotADirectoryError(
                f'{guidelines_dir} is not a directory.')

        # By default the rules directory is a sibling of the guidelines
        # directory: <...>/config/guidelines and <...>/config/rules.
        if rules_dir is None:
            rules_dir = os.path.join(
                os.path.dirname(os.path.normpath(guidelines_dir)), 'rules')

        # Rule details are the single source of truth for title/url.
        # { rule_id: { "title": ..., "rule_url": ... } }
        self.__rule_details = self.__load_rule_details(rules_dir)

        # Guideline membership and metadata.
        # { guideline: { rule_id: { "title": ..., "rule_url": ... } } }
        # { guideline: { "title": ..., "url": ... } }
        self.__all_rules, self.__guideline_meta = \
            self.__union_guideline_files(guidelines_dir)

        # Reverse index: { rule_id: [ guideline, ... ] }
        self.__rule_to_guidelines: defaultdict[str, List[str]] = \
            defaultdict(list)
        for guideline_name, rules in self.__all_rules.items():
            for rule_id in rules:
                self.__rule_to_guidelines[rule_id].append(guideline_name)

    def __load_rule_details(
        self,
        rules_dir: str
    ) -> dict[str, dict[str, str]]:
        """
        Load every rule descriptor file from the rules directory. Each file is
        a flat list of dictionaries with at least a 'rule_id' key and optional
        'title' and 'rule_url' keys. Returns a mapping from rule id to its
        details.
        """
        rule_details: dict[str, dict[str, str]] = {}

        if not os.path.isdir(rules_dir):
            LOG.warning("Rules directory '%s' does not exist. Rule details "
                        "(title, url) will be empty.", rules_dir)
            return rule_details

        rule_files = filter(
            lambda f: f.endswith('.yaml') or f.endswith('.yml'),
            os.listdir(rules_dir))

        for rule_file in rule_files:
            rule_path = os.path.join(rules_dir, rule_file)
            rules_data = load_yaml(rule_path)

            if not isinstance(rules_data, list):
                LOG.warning("%s does not contain a list of rules.", rule_path)
                continue

            for rule in rules_data:
                if not isinstance(rule, dict) or 'rule_id' not in rule:
                    LOG.warning("A rule in %s has no 'rule_id'.", rule_path)
                    continue

                rule_id = rule['rule_id']
                rule_details[rule_id] = {
                    'title': rule.get('title', ''),
                    'rule_url': rule.get('rule_url', '')
                }

        return rule_details

    def __check_guideline_format(self, guideline_data: dict):
        """
        Check the format of a guideline. It must contain specific values with
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
                "The 'rules' field must exist and be a list of dictionaries.")

        if any(map(lambda rule: "rule_id" not in rule
           or not isinstance(rule["rule_id"], str), rules)):
            raise ValueError(
                "All rules must have 'rule_id' that is a string.")

    def __union_guideline_files(
        self,
        guidelines_dir: str
    ) -> tuple[defaultdict[str, dict[str, dict[str, str]]],
               dict[str, dict[str, str]]]:
        """
        Create a union object of the guideline descriptor files. Each guideline
        descriptor references rule ids only; the rule details (title, url) are
        joined in from the rules descriptors loaded separately.

        Returns a tuple of:
          all_rules -- maps guidelines to the collection of their rules:
            {
                "guideline1": {
                    "rule_id1": { "title": ..., "rule_url": ... },
                    "rule_id2": { ... }
                },
                "guideline2": { ... }
            }
          guideline_meta -- maps guidelines to their metadata:
            {
                "guideline1": { "title": ..., "url": ... },
                ...
            }
        """
        guideline_files = map(
            lambda f: os.path.join(guidelines_dir, f),
            filter(lambda f: f.endswith('.yaml') or f.endswith('.yml'),
                   os.listdir(guidelines_dir)))

        all_rules: defaultdict[
            str, dict[str, dict[str, str]]] = defaultdict(dict)
        guideline_meta: dict[str, dict[str, str]] = {}

        for guideline_file in guideline_files:
            guideline_data = load_yaml(guideline_file)

            try:
                self.__check_guideline_format(guideline_data)

                guideline_name = guideline_data["guideline"]
                rules = guideline_data["rules"]

                all_rules[guideline_name] = {
                    rule["rule_id"]: self.__details_of(rule)
                    for rule in rules
                }

                guideline_meta[guideline_name] = {
                    "title": guideline_data.get("guideline_title", ""),
                    "url": guideline_data.get("guideline_url", "")
                }
            except ValueError as ex:
                LOG.warning("%s does not have a correct guideline format.",
                            guideline_file)
                LOG.warning(ex)

        return all_rules, guideline_meta

    def __details_of(self, rule: dict) -> dict[str, str]:
        """
        Return the details (title, url) of a rule. The single source of truth
        is the rules descriptor. If the guideline descriptor itself carries
        inline 'title'/'rule_url' (legacy format) those are used as a fallback
        when the rule is not present among the loaded rule details.
        """
        rule_id = rule["rule_id"]

        if rule_id in self.__rule_details:
            return dict(self.__rule_details[rule_id])

        return {
            "title": rule.get("title", ""),
            "rule_url": rule.get("rule_url", "")
        }

    def rules_of_guideline(
        self,
        guideline_name: str,
    ) -> dict[str, dict[str, str]]:
        """
        Return the rules of a guideline as a mapping from rule id to its
        details (title, url).
        """
        return self.__all_rules[guideline_name]

    def guidelines_of_rule(self, rule_id: str) -> List[str]:
        """
        Return the list of guidelines that contain the given rule id.
        """
        return list(self.__rule_to_guidelines.get(rule_id, []))

    def rule_details(self, rule_id: str) -> dict[str, str]:
        """
        Return the details (title, url) of a single rule id. If the rule id is
        unknown an empty details dictionary is returned.
        """
        return dict(self.__rule_details.get(
            rule_id, {"title": "", "rule_url": ""}))

    def guideline_titles(self) -> dict[str, str]:
        """
        Return a mapping from guideline name to its title.
        """
        return {name: meta.get("title", "")
                for name, meta in self.__guideline_meta.items()}

    def guideline_urls(self) -> dict[str, str]:
        """
        Return a mapping from guideline name to its url.
        """
        return {name: meta.get("url", "")
                for name, meta in self.__guideline_meta.items()}

    def all_guidelines(self) -> Iterable[str]:
        """
        Return the names of all existing guidelines.
        """
        return list(self.__all_rules.keys())

    def all_guideline_rules(
        self
    ) -> defaultdict[str, dict[str, dict[str, str]]]:
        return self.__all_rules
