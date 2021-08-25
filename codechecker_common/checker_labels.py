import os
from collections import defaultdict
from itertools import chain
from typing import Dict, Iterable, List, Tuple, Union
from codechecker_common.util import load_json_or_empty


class CheckerLabels:
    # These labels should be unique by each analyzer. If this uniqueness is
    # violated then an error is thrown during label JSON file parse. The
    # default value of the label also needs to be provided here.
    UNIQUE_LABELS = {
        'severity': 'UNSPECIFIED'}

    def __init__(self, checker_labels_dir: str):
        if not os.path.isdir(checker_labels_dir):
            raise NotADirectoryError(
                f'{checker_labels_dir} is not a directory.')

        label_json_files = os.listdir(
            os.path.join(checker_labels_dir, 'analyzers'))

        self.__descriptions = {}

        if 'descriptions.json' in os.listdir(checker_labels_dir):
            self.__descriptions = load_json_or_empty(os.path.join(
                checker_labels_dir, 'descriptions.json'))

        label_json_files = map(
            lambda f: os.path.join(checker_labels_dir, 'analyzers', f),
            label_json_files)

        self.__data = self.__union_label_files(label_json_files)
        self.__check_json_format(self.__data)

    def __union_label_files(
        self,
        label_files: Iterable[str]
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        This function creates an union object of the given label files. The
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
            data = load_json_or_empty(label_file)
            analyzer_labels = defaultdict(list)

            for checker, labels in data['labels'].items():
                analyzer_labels[checker].extend(labels)

            all_labels[data['analyzer']] = analyzer_labels

        return all_labels

    def __get_label_key_value(self, key_value: str) -> Tuple[str, str]:
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

    def __check_json_format(self, data: dict) -> bool:
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
            for k, _ in map(self.__get_label_key_value, labels):
                if k == label:
                    if found:
                        return False
                    else:
                        found = True
            return True

        if not isinstance(data, dict):
            raise ValueError(f'Top level element should be a JSON object.')

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
                            f'Label "severity" should be unique for checker '
                            '{checker}.')

    def __get_analyzer_data(self, analyzers: Iterable[str]):
        for analyzer, checkers in self.__data.items():
            if analyzers is None or analyzer in analyzers:
                yield analyzer, checkers

    def checkers_by_labels(
        self,
        filter_labels: Iterable[str],
        analyzers: Iterable[str] = None
    ) -> List[str]:
        """
        Returns a list of checkers that have at least one of the specified
        labels.

        filter_labels -- A string list which contains labels with specified
                         values. E.g. ['profile:default', 'severity:high'].
        analyzers -- A list of analyzers among which checkers are searched.
                     By default all analyzers are searched.
        """
        collection = []

        filter_labels = set(map(self.__get_label_key_value, filter_labels))

        for _, checkers in self.__get_analyzer_data(analyzers):
            for checker, labels in checkers.items():
                labels = set(map(self.__get_label_key_value, labels))

                if labels.intersection(filter_labels):
                    collection.append(checker)

        return collection

    def label_of_checker(
        self,
        checker: str,
        label: str,
        analyzers: Iterable[str] = None
    ) -> Union[str, List[str]]:
        """
        If a label has unique constraint then this function retuns the value
        that belongs to the given label or the default value that is set among
        label constraints. If there is no unique constraint then an iterable
        object returns with the values assigned to the given label. If the
        checker name is not found in the label config file then its prefixes
        are also searched. For example "clang-diagnostic" in the config file
        matches "clang-diagnostic-unused-argument".
        """
        labels = chain.from_iterable([])

        for analyzer, _ in self.labels_of_checker(checker, analyzers):
            if analyzers is None or analyzer in analyzers:
                labels = chain(labels, filter(
                    lambda lab: lab[0] == label,
                    self.labels_of_checker(checker)))

        if label in CheckerLabels.UNIQUE_LABELS:
            try:
                return next(labels)[1]
            except Exception:
                return CheckerLabels.UNIQUE_LABELS[label]

        # TODO set() is used for uniqueing results in case a checker name is
        # provided by multiple analyzers. This will be unnecessary when we
        # cover this case properly.
        return list(set(map(lambda value: value[1], labels)))

    def severity(self, checker: str, analyzers: Iterable[str] = None) -> str:
        """
        Shorthand for the following call:
        checker_labels.label_of_checker(checker, 'severity', analyzers)
        """
        return self.label_of_checker(checker, 'severity', analyzers)

    def labels_of_checker(
        self,
        checker: str,
        analyzers: Iterable[str] = None
    ) -> List[str]:
        """
        Return the list of labels of a checker. The list contains (label,
        value) pairs. If the checker name is not found in the label config file
        then its prefixes are also searched. For example "clang-diagnostic" in
        the config file matches "clang-diagnostic-unused-argument".
        """
        labels = []

        for _, checkers in self.__get_analyzer_data(analyzers):
            c = checker

            if c not in checkers:
                c = next(filter(
                    lambda c: checker.startswith(c),
                    iter(checkers.keys())), None)

            labels.extend(
                map(self.__get_label_key_value, checkers.get(c, [])))

        # TODO set() is used for uniqueing results in case a checker name is
        # provided by multiple analyzers. This will be unnecessary when we
        # cover this case properly.
        return list(set(labels))

    def get_description(self, label: str) -> Dict[str, str]:
        """
        Returns the descriptions of the given label's values.
        """
        return self.__descriptions.get(label)

    def checkers(self, analyzers: Iterable[str] = None) -> List[str]:
        """
        Return the list of available checkers.
        """
        collection = []

        for _, checkers in self.__get_analyzer_data(analyzers):
            collection.extend(checkers.keys())

        return collection

    def labels(self, analyzers: Iterable[str] = None) -> List[str]:
        """
        Returns a list of occurring labels.
        """
        collection = set()

        for _, checkers in self.__get_analyzer_data(analyzers):
            for labels in checkers.values():
                collection.update(map(
                    lambda x: self.__get_label_key_value(x)[0], labels))

        return list(collection)

    def occurring_values(
        self,
        label: str,
        analyzers: Iterable[str] = None
    ) -> List[str]:
        """
        Return the list of values belonging to the given label which were used
        for at least one checker.
        """
        values = set()

        for _, checkers in self.__get_analyzer_data(analyzers):
            for labels in checkers.values():
                for lab, value in map(self.__get_label_key_value, labels):
                    if lab == label:
                        values.add(value)

        return list(values)
