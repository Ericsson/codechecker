# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
from collections import defaultdict
import os

from typing import Any, cast, Iterable, List

from codechecker_common.util import load_json


def split_label_kv(key_value: str) -> tuple[str, str]:
    """
    A label has a value separated by colon (:) character, e.g:
    "severity:high". This function returns this key and value as a tuple.
    Optional whitespaces around (:) and at the two ends of this string are
    not taken into account. If key_value contains no colon, then the value
    is empty string.
    """
    try:
        pos = key_value.index(':')
    except ValueError:
        return (key_value.strip(), '')

    return key_value[:pos].strip(), key_value[pos + 1:].strip()


# TODO: Most of the methods of this class get an optional analyzer name. If
# None is given to these functions then labels of any analyzer's checkers is
# taken into account. This the union of all analyzers' checkers is a bad
# approach because different analyzers may theoretically have checkers with the
# same name. Fortunately this is not the case with the current analyzers'
# checkers, so now it works properly.
class CheckerLabels:
    # These labels should be unique by each analyzer. If this uniqueness is
    # violated then an error is thrown during label JSON file parse. The
    # default value of the label also needs to be provided here.
    UNIQUE_LABELS = {
        'severity': 'UNSPECIFIED',
        'blacklist': 'false',
        'description': ''}

    def __init__(self, checker_labels_dir: str, guidelines=None):
        if not os.path.isdir(checker_labels_dir):
            raise NotADirectoryError(
                f'{checker_labels_dir} is not a directory.')

        # Optional Guidelines object. When provided, the guidelines a checker
        # belongs to are derived in memory from its "rule:<rule_id>" labels.
        self.__guidelines = guidelines

        label_json_files: Iterable[str] = os.listdir(
            os.path.join(checker_labels_dir, 'analyzers'))

        self.__descriptions = {}

        if 'descriptions.json' in os.listdir(checker_labels_dir):
            self.__descriptions = load_json(os.path.join(
                checker_labels_dir, 'descriptions.json'))

        # Profile containment maps a profile to the profiles it also implies.
        # E.g. { "extreme": ["sensitive"], "sensitive": ["default"] } means a
        # checker labeled with "extreme" also belongs to "sensitive" and
        # "default". The relation is applied transitively.
        self.__profile_containment = \
            self.__descriptions.get('profile-containment', {})

        label_json_files = map(
            lambda f: os.path.join(checker_labels_dir, 'analyzers', f),
            label_json_files)

        self.__data = self.__union_label_files(label_json_files)
        self.__check_json_format(self.__data)

    def __union_label_files(
        self,
        label_files: Iterable[str]
    ) -> dict[str, defaultdict[str, list[str]]]:
        """
        This function creates a union object of the given label files. The
        resulting object maps analyzers to the collection of their checkers
        with their labels:

        {
            "analyzer1": {
                "checker1": [ ... ]
                "checker2": [ ... ]
            },
            "analyzer2": {
                ...
            }
        }
        """
        all_labels = {}

        for label_file in label_files:
            data = load_json(label_file)
            analyzer_labels = defaultdict(list)

            for checker, labels in data['labels'].items():
                analyzer_labels[checker].extend(labels)

            all_labels[data['analyzer']] = analyzer_labels

        return all_labels

    def __check_json_format(self, data: dict):
        """
        Check the format of checker labels' JSON config file, i.e. this file
        must contain specific values with specific types. For example the
        checker labels are string lists. In case of any format error a
        ValueError exception is thrown with the description of the wrong
        format.
        """
        def is_string_list(x):
            return isinstance(x, list) and \
                all(map(lambda s: isinstance(s, str), x))

        def is_unique(labels: Iterable[str], label: str):
            """
            Check if the given label occurs only once in the label list.
            """
            found = False
            for k, _ in map(split_label_kv, labels):
                if k == label:
                    if found:
                        return False
                    found = True
            return True

        if not isinstance(data, dict):
            raise ValueError('Top level element should be a JSON object.')

        for _, checkers in data.items():
            for checker, labels in checkers.items():
                if not is_string_list(labels):
                    raise ValueError(
                        f'"{checker}" should be assigned a string list.')

                if any(map(lambda s: ':' not in s, labels)):
                    raise ValueError(
                        f'All labels at "{checker}" should be in the '
                        'following format: <label>:<property>.')

                for unique_label in CheckerLabels.UNIQUE_LABELS:
                    if not is_unique(labels, unique_label):
                        raise ValueError(
                            'Label "severity" should be unique for checker '
                            f'{checker}.')

    def __get_analyzer_data(
        self,
        analyzer: str | None = None
    ) -> Iterable[tuple[str, Any]]:
        """
        Most functions of this class require an analyzer name which determines
        a checker name specifically. If no analyzer is given then all of them
        is taken into account (for backward-compatibility reasons). This helper
        function yields either an analyzer's label data or all analyzer's
        label data.
        """
        for a, c in self.__data.items():
            if analyzer is None or a == analyzer:
                yield a, c

    def __expand_query_profiles(self, profiles: Iterable[str]) -> List[str]:
        """
        Expand the requested profile values of a query through the
        profile-containment relation. The containment maps a profile to the
        profiles it contains, e.g. {"extreme": ["sensitive"],
        "sensitive": ["default"]}. Filtering by a profile also matches the
        checkers of the profiles it contains, applied transitively:

          query "default"   -> matches {default}
          query "sensitive" -> matches {sensitive, default}
          query "extreme"   -> matches {extreme, sensitive, default}

        This way "default" is the smallest set (only default-labeled
        checkers), "sensitive" additionally includes default-labeled checkers,
        and "extreme" includes default- and sensitive-labeled checkers too.
        The result preserves uniqueness.
        """
        result: List[str] = []
        stack = list(profiles)

        while stack:
            profile = stack.pop()
            if profile in result:
                continue
            result.append(profile)
            stack.extend(self.__profile_containment.get(profile, []))

        return result

    def __expand_filter_labels(
        self,
        filter_labels: Iterable[tuple[str, str]]
    ) -> set[tuple[str, str]]:
        """
        Expand the (label, value) pairs of a filter so that profile filters
        also match the profiles they contain (see __expand_query_profiles).
        Non-profile labels are kept unchanged.
        """
        expanded: set[tuple[str, str]] = set()

        for key, value in filter_labels:
            if key == 'profile':
                for prof in self.__expand_query_profiles([value]):
                    expanded.add(('profile', prof))
            else:
                expanded.add((key, value))

        return expanded

    def __derived_guidelines(
        self,
        rule_values: Iterable[str]
    ) -> List[tuple[str, str]]:
        """
        Derive the guideline labels of a checker from its rule values. For
        every "rule:<rule_id>" of a checker the guidelines that contain the
        given rule are looked up and returned as ("guideline", <name>) pairs.
        Requires a Guidelines object to be injected; without it an empty list
        is returned.
        """
        if self.__guidelines is None:
            return []

        guidelines: List[tuple[str, str]] = []
        seen: set[str] = set()

        for rule_id in rule_values:
            for guideline in self.__guidelines.guidelines_of_rule(rule_id):
                if guideline not in seen:
                    seen.add(guideline)
                    guidelines.append(('guideline', guideline))

        return guidelines

    def __augment_labels(
        self,
        labels: List[tuple[str, str]]
    ) -> List[tuple[str, str]]:
        """
        Augment a checker's raw (label, value) pairs with the information that
        is derived in memory. Currently this derives the guideline labels from
        the checker's rule values. The checker's profile label is left as its
        single tier; the containment relation is applied on the query side
        (see __expand_filter_labels) instead of expanding checker membership.
        """
        rule_values = [value for key, value in labels if key == 'rule']

        augmented: List[tuple[str, str]] = list(labels)
        augmented.extend(self.__derived_guidelines(rule_values))

        return augmented

    def get_analyzers(self) -> Iterable[str]:
        return self.__data.keys()

    def checkers_by_labels(
        self,
        filter_labels: Iterable[str],
        analyzer: str | None = None
    ) -> list[str]:
        """
        Returns a list of checkers that have at least one of the specified
        labels.

        filter_labels -- A string list which contains labels with specified
                         values. E.g. ['profile:default', 'severity:high'].
        analyzer -- An optional analyzer name of which checkers are searched.
                    By default all analyzers are searched.
        """
        collection = []

        label_set = self.__expand_filter_labels(
            map(split_label_kv, filter_labels))

        for _, checkers in self.__get_analyzer_data(analyzer):
            for checker, labels in checkers.items():
                labels = set(self.__augment_labels(
                    list(map(split_label_kv, labels))))

                if labels.intersection(label_set):
                    collection.append(checker)

        return collection

    def label_of_checker(
        self,
        checker: str,
        label: str,
        analyzer: str | None = None
    ) -> str | list[str]:
        """
        If a label has unique constraint then this function retuns the value
        that belongs to the given label or the default value that is set among
        label constraints. If there is no unique constraint then an iterable
        object returns with the values assigned to the given label. If the
        checker name is not found in the label config file then its prefixes
        are also searched. For example "clang-diagnostic" in the config file
        matches "clang-diagnostic-unused-argument".
        """
        labels = (
            value
            for key, value in self.labels_of_checker(checker, analyzer)
            if key == label)

        if label in CheckerLabels.UNIQUE_LABELS:
            try:
                return next(labels)
            except StopIteration:
                return CheckerLabels.UNIQUE_LABELS[label]

        # TODO set() is used for uniqueing results in case a checker name is
        # provided by multiple analyzers. This will be unnecessary when we
        # cover this case properly.
        return list(set(labels))

    def severity(self, checker: str, analyzer: str | None = None) -> str:
        """
        Shorthand for the following call:
        checker_labels.label_of_checker(checker, 'severity', analyzer)
        """
        return cast(str, self.label_of_checker(checker, 'severity', analyzer))

    def labels_of_checker(
        self,
        checker: str,
        analyzer: str | None = None
    ) -> list[tuple[str, str]]:
        """
        Return the list of labels of a checker. The list contains (label,
        value) pairs. If the checker name is not found in the label config file
        then its prefixes are also searched. For example "clang-diagnostic" in
        the config file matches "clang-diagnostic-unused-argument".
        """
        labels: list[tuple[str, str]] = []

        for _, checkers in self.__get_analyzer_data(analyzer):
            c: str | None = checker

            if c not in checkers:
                c = next(filter(
                    lambda c: checker.startswith(cast(str, c)),
                    iter(checkers.keys())), None)

            labels.extend(map(split_label_kv, checkers.get(c, [])))

        labels = self.__augment_labels(labels)

        # TODO set() is used for uniqueing results in case a checker name is
        # provided by multiple analyzers. This will be unnecessary when we
        # cover this case properly.
        return list(set(labels))

    def get_description(self, label: str) -> dict[str, str]:
        """
        Returns the descriptions of the given label's values.
        """
        return self.__descriptions.get(label, {})

    def checkers(self, analyzer: str | None = None) -> list[str]:
        """
        Return the list of available checkers.
        """
        collection = []

        for _, checkers in self.__get_analyzer_data(analyzer):
            collection.extend(checkers.keys())

        return collection

    def labels(self, analyzer: str | None = None) -> list[str]:
        """
        Returns a list of occurring labels. When a Guidelines object is
        available the derived "guideline" label is also reported, since a
        checker's guidelines are derived in memory from its "rule" labels.
        """
        collection: set[str] = set()

        for _, checkers in self.__get_analyzer_data(analyzer):
            for labels in checkers.values():
                collection.update(map(
                    lambda x: split_label_kv(x)[0], labels))

        if self.__guidelines is not None:
            collection.add('guideline')

        return list(collection)

    def occurring_values(
        self,
        label: str,
        analyzer: str | None = None
    ) -> list[str]:
        """
        Return the list of values belonging to the given label which were used
        for at least one checker.
        """
        # Guidelines are derived from rules, so their values come from the
        # Guidelines object rather than from raw labels.
        if label == 'guideline' and self.__guidelines is not None:
            return list(self.__guidelines.all_guidelines())

        values = set()

        for _, checkers in self.__get_analyzer_data(analyzer):
            for labels in checkers.values():
                for lab, value in map(split_label_kv, labels):
                    if lab == label:
                        values.add(value)

        return list(values)
