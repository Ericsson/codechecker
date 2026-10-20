# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import os
from dataclasses import dataclass, field
from collections import defaultdict

from codechecker_common.util import load_yaml
from codechecker_common.logger import get_logger

LOG = get_logger('system')


@dataclass(frozen=True)
class Rule:
    """Detailed descriptor of a single rule."""
    rule_id: str
    title: str = ""
    rule_url: str = ""


@dataclass
class Guideline:
    """A named grouping of rules, mapping rule id to its Rule descriptor."""
    guideline_id: str
    title: str = ""
    rules: dict[str, Rule] = field(default_factory=dict)


class Guidelines:
    """
    Represents the guideline and rule descriptors.

    A guideline (e.g. "sei-cert-c") is a group of rule ids. Guideline
    descriptors contains the group id, title and assigned rules and are placed
    in the guidelines directory. The detailed information of a rule (title,
    url) is stored in a separate file in the rules directory (one file per
    rule type, e.g. "cwe-rules.yaml") and it is the single source of truth
    for rule's details.

    This class joins the two sources:
      - The guideline membership comes from the guideline descriptors,
      - All rule details (title, url) come from the rules descriptors,
    and it provides a reverse lookup from a rule id to the guidelines that
    contain it.
    """

    def __init__(self, guidelines_dir: str):
        if not os.path.isdir(guidelines_dir):
            raise NotADirectoryError(
                f'{guidelines_dir} is not a directory.')

        # Resolve the rules directory from the guidelines dir path since it
        # is a direct sibling of it (config/guidelines, config/rules)
        rules_dir = os.path.join(
            os.path.dirname(os.path.normpath(guidelines_dir)), 'rules')

        self.__rule_details = self.__load_rule_details(rules_dir)

        self.__guidelines = self.__union_guideline_files(guidelines_dir)

        # Reverse index for checking which rule is being contained
        # in which guideline. Without this, the lookup is slow.
        # Format: { rule_id: [ guideline_id, ... ] }
        self.__rule_to_guidelines: defaultdict[str, list[str]] = \
            defaultdict(list)
        for guideline_id, guideline in self.__guidelines.items():
            for rule_id in guideline.rules:
                self.__rule_to_guidelines[rule_id].append(guideline_id)

    def __load_rule_details(
        self,
        rules_dir: str
    ) -> dict[str, Rule]:
        """
        Load rule metadata from each rule descriptor file from the rules
        directory. Each file contains a list of dictionaries with a 'rule_id'
        and optional 'title' and 'rule_url'.
        Returns a rule_id:Rule object pair.
        """
        rule_details: dict[str, Rule] = {}

        if not os.path.isdir(rules_dir):
            LOG.warning("Rules directory '%s' does not exist. Rule details "
                        "(title, url) will be empty.", rules_dir)
            return rule_details

        rule_files = filter(
            lambda f: f.endswith('.yaml'),
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
                rule_details[rule_id] = Rule(
                    rule_id=rule_id,
                    title=rule.get('title', ''),
                    rule_url=rule.get('rule_url', ''))

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
    ) -> dict[str, Guideline]:
        """
        Build the guideline objects from the guideline and rule descriptors.
        The guideline metadata is read from the guideline descriptor along
        with the rule ids and the rule metadata is added from the rule files.
        Returns a guideline_id:Guideline object pair.
        """
        guideline_files = map(
            lambda f: os.path.join(guidelines_dir, f),
            filter(lambda f: f.endswith('.yaml'),
                   os.listdir(guidelines_dir)))

        guidelines: dict[str, Guideline] = {}

        for guideline_file in guideline_files:
            guideline_data = load_yaml(guideline_file)

            if not isinstance(guideline_data, dict):
                LOG.warning("%s does not contain a guideline.", guideline_file)
                continue

            try:
                self.__check_guideline_format(guideline_data)

                guideline_id = guideline_data["guideline"]
                guidelines[guideline_id] = Guideline(
                    guideline_id=guideline_id,
                    title=guideline_data["guideline_title"],
                    rules={rule["rule_id"]: self.__rule_of(rule)
                           for rule in guideline_data["rules"]})
            except ValueError as ex:
                LOG.warning("%s does not have a correct guideline format.",
                            guideline_file)
                LOG.warning(ex)

        return guidelines

    def __rule_of(self, rule: dict) -> Rule:
        """
        Return the Rule for a guideline's rule reference. The rules descriptor
        is the single source of truth; a guideline's inline 'title'/'rule_url'
        (legacy format) is used as a fallback when the rule is unknown.
        """
        rule_id = rule["rule_id"]

        if rule_id in self.__rule_details:
            return self.__rule_details[rule_id]

        return Rule(
            rule_id=rule_id,
            title=rule.get("title", ""),
            rule_url=rule.get("rule_url", ""))

    def rules_of_guideline(self, guideline_id: str) -> dict[str, Rule]:
        """
        Return the rules of a guideline as a mapping from rule id to its Rule.
        """
        guideline = self.__guidelines.get(guideline_id)
        return guideline.rules if guideline is not None else {}

    def guidelines_of_rule(self, rule_id: str) -> list[str]:
        """
        Return the list of guidelines that contain the given rule id.
        """
        return list(self.__rule_to_guidelines.get(rule_id, []))

    def rule_details(self, rule_id: str) -> Rule:
        """
        Return the Rule of a single rule id. If the rule id is unknown a Rule
        with empty details is returned.
        """
        return self.__rule_details.get(rule_id, Rule(rule_id=rule_id))

    def all_guidelines(self) -> list[str]:
        """
        Return the ids of all existing guidelines in a deterministic
        (alphabetical) order, independent of the file system listing order.
        """
        return sorted(self.__guidelines.keys())
