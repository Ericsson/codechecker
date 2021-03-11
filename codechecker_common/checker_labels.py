from collections import defaultdict
from codechecker_common.util import load_json_or_empty


class CheckerLabels:
    def __init__(self, checker_labels_filename):
        self.__data = load_json_or_empty(checker_labels_filename)
        self.__check_json_format(self.__data, checker_labels_filename)

    def __get_label_key_value(self, key_value):
        """
        A label has a value separated by colon (:) character, e.g:
        "severity:high". This function returns this key and value as a tuple.
        Optional whitespaces around (:) and at the two ends of this string are
        not taken into account.
        """
        pos = key_value.index(':')
        return key_value[:pos].strip(), key_value[pos + 1:].strip()

    def __check_json_format(self, data, checker_labels_filename):
        """
        Check the format of checker labels' JSON config file, i.e. this file
        must contain specific values with specific types. For example the
        checker labels are string lists. In case of any format error a
        ValueError exception is thrown with the description of the wrong
        format.
        """
<<<<<<< Updated upstream
        header = f'Format error in {checker_labels_filename}:'

        def is_string_list(l):
            return isinstance(l, list) and \
                all(map(lambda s: isinstance(s, str), l))
=======
        def is_string_list(x):
            return isinstance(x, list) and \
                all(map(lambda s: isinstance(s, str), x))
>>>>>>> Stashed changes

        def check_constraints(checker, labels):
            key_counts = defaultdict(int)
            key_values = defaultdict(set)

            for label in labels:
                key, value = self.__get_label_key_value(label)
                key_counts[key] += 1
                key_values[key].add(value)

                if key not in self.__data['constraints']:
                    raise ValueError(
                        f'{header} label "{key}" at "{checker}" should '
                        'occur in "constraints" section.')

            for label, properties in self.__data['constraints'].items():
                if 'choice' in properties:
                    for key, values in key_values.items():
                        if key != label:
                            continue

                        if not (values <= set(properties['choice'])):
                            choices = ', '.join(properties['choice'])
                            raise ValueError(
                                f'{header} label "{label}" at "{checker}" '
                                f'should be one of {choices}.')

                if properties.get('required') and label not in key_counts:
                    raise ValueError(
                        f'{header} label "{label}" at "{checker}" is '
                        'required.')

                if properties.get('unique') and key_counts[label] > 1:
                    raise ValueError(
                        f'{header} label "{label}" at "{checker}" must be '
                        'unique.')

        if not isinstance(data, dict):
            raise ValueError(
                f'{header} top level element should be a JSON object.')

        if 'constraints' not in data or 'labels' not in data:
            raise ValueError(
                f'{header} "constraints" and "labels" are required keys.')

        constraints = data['constraints']
        labels = data['labels']

        if not isinstance(constraints, dict) or not isinstance(labels, dict):
            raise ValueError(
                f'{header} "constraints" and "labels" should be assigned JSON '
                'objects.')

        for label, properties in constraints.items():
            if not isinstance(properties, dict):
                raise ValueError(
                    f'{header} Constraints of "{label}" should be described '
                    'by a JSON object.')

            for property, value in properties.items():
                if property == 'choice' and not isinstance(value, dict):
                    raise ValueError(
                        f'{header} label "choice" should be assigned a JSON '
                        'object.')
                elif property == 'required' and not isinstance(value, bool):
                    raise ValueError(
                        f'{header} label "required" should be assigned a '
                        'boolean value.')
                elif property == 'unique' and not isinstance(value, bool):
                    raise ValueError(
                        f'{header} label "unique" should be assigned a '
                        'boolean value.')
                elif property == 'default' and not isinstance(value, str):
                    raise ValueError(
                        f'{header} label "default" should be assigned a '
                        'string value.')

            if properties.get('default') and not properties.get('unique'):
                raise ValueError(
                    f'{header} "default" value can belong to labels only '
                    'with "unique" constraint.')

        for checker, labels in labels.items():
            if not is_string_list(labels):
                raise ValueError(
                    f'{header} "{checker}" should be assigned a string list.')

            if any(map(lambda s: ':' not in s, labels)):
                raise ValueError(
                    f'{header} all labels at "{checker}" should be in the '
                    'following format: <label>:<property>.')

            check_constraints(checker, labels)

    def checkers_by_labels(self, filter_labels):
        """
        Returns a list of checkers that have at least one of the specified
        labels.

        filter_labels -- A string list which contains labels with specified
                         values. E.g. ['profile:default', 'severity:high'].
        """
        checkers = []

        filter_labels = set(map(self.__get_label_key_value, filter_labels))

        for checker, labels in self.__data['labels'].items():
            labels = set(map(self.__get_label_key_value, labels))

            if labels.intersection(filter_labels):
                checkers.append(checker)

        return checkers

    def label_of_checker(self, checker, label):
        """
        If a label has unique constraint then this function retuns the value
        that belongs to the given label or the default value that is set among
        label constraints. If there is no unique constraint then an iterable
        object returns with the values assigned to the given label. If the
        checker name is not found in the label config file then its prefixes
        are also searched. For example "clang-diagnostic" in the config file
        matches "clang-diagnostic-unused-argument".
        """
        labels = filter(
            lambda lab: lab[0] == label,
            self.labels_of_checker(checker))

        if self.__data['constraints'].get(label, {}).get('unique'):
            try:
                return next(labels)[1]
            except Exception as ex:
                return self.__data['constraints'].get(label, {}).get('default')

        return map(lambda _, value: value, labels)

    def labels_of_checker(self, checker):
        """
        Return the list of labels of a checker. The list contains (label,
        value) pairs. If the checker name is not found in the label config file
        then its prefixes are also searched. For example "clang-diagnostic" in
        the config file matches "clang-diagnostic-unused-argument".
        """
        if checker not in self.__data['labels']:
            checker = next(filter(
                lambda c: checker.startswith(c),
                iter(self.__data['labels'].keys())), None)

        return map(
            self.__get_label_key_value,
            self.__data['labels'].get(checker, []))

    def get_constraint(self, label, constraint):
        """
        Returns the constraints of a label. If there is no such constraint on
        this label then None returns.

        label -- The name of a label, for example 'profile' or 'severity'.
        constraint -- One of 'choice', 'unique' or 'required'.
        """
        return self.__data['constraints'].get(label, {}).get(constraint)

    def checkers(self):
        """
        Return the list of available checkers.
        """
        return self.__data['labels'].keys()

    def labels(self):
        """
        Return the list of available labels.
        """
        return self.__data['constraints'].keys()

    def occurring_values(self, label):
        """
        Return the list of values belonging to the given label which were used
        for at least one checker.
        """
        values = set()

        for labels in self.__data['labels'].values():
            for lab, value in map(self.__get_label_key_value, labels):
                if lab == label:
                    values.add(value)

        return list(values)
