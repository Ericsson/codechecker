# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
""""""

import hashlib


class BuildAction(object):
    def __init__(self, build_action_id=0):
        self._id = build_action_id
        self._analyzer_options = []
        self._compiler_includes = []
        self._analyzer_type = -1
        self._original_command = ''
        self._directory = ''
        self._output = ''
        self._lang = None
        self._target = ''
        self._source_count = 0
        self._sources = []
        self._skip = False

    def __str__(self):
        # For debugging.
        return ('Id: {0} ,\nOriginal command: {1},\n'
                'Analyzer type: {2},\n Analyzer options: {3},\n'
                'Directory: {4},\nOutput: {5},\nLang: {6},\nTarget: {7},\n'
                'Source count {8},\nSources: {9}'). \
            format(self._id, self._original_command,
                   self._analyzer_type, self._analyzer_options,
                   self._directory, self._output, self._lang, self._target,
                   self._source_count, self._sources)

    @property
    def analyzer_type(self):
        """
        Stores which type of analyzer should be run in this buildaction.
        """
        return self._analyzer_type

    @analyzer_type.setter
    def analyzer_type(self, value):
        """
        Stores which type of analyzer should be run in this buildaction.
        """
        self._analyzer_type = value

    @property
    def id(self):
        return self._id

    @property
    def compiler_includes(self):
        return self._compiler_includes

    @compiler_includes.setter
    def compiler_includes(self, value):
        self._compiler_includes = value

    @property
    def analyzer_options(self):
        return self._analyzer_options

    @analyzer_options.setter
    def analyzer_options(self, value):
        """
        A filtered compile arguments which will be forwarded to the analyzer.
        """
        self._analyzer_options = value

    @property
    def original_command(self):
        return self._original_command

    @property
    def original_command_hash(self):
        hash_object = hashlib.sha1(self._original_command)
        hex_dig = hash_object.hexdigest()
        return hex_dig

    @original_command.setter
    def original_command(self, value):
        self._original_command = value

    @property
    def directory(self):
        return self._directory

    @directory.setter
    def directory(self, value):
        self._directory = value

    @property
    def output(self):
        return self._output

    @output.setter
    def output(self, value):
        self._output = value

    @property
    def source_count(self):
        return self._source_count

    @source_count.setter
    def source_count(self, count):
        self._source_count = count

    @property
    def sources(self):
        for source in self._sources:
            yield source

    @sources.setter
    def sources(self, value):
        self._sources.append(value)
        self._source_count += 1

    @property
    def lang(self):
        return self._lang

    @lang.setter
    def lang(self, value):
        self._lang = value

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, value):
        self._target = value

    @property
    def skip(self):
        return self._skip

    @skip.setter
    def skip(self, value):
        self._skip = value

    def __eq__(self, other):
        return other._original_command == self._original_command

    @property
    def cmp_key(self):
        """
        If the compilation database contains the same compilation action
        multiple times it should be checked only once.
        Use this key to compare compilation commands for the analysis.
        """
        hash_content = []
        hash_content.extend(self.analyzer_options)
        hash_content.append(str(self._analyzer_type))
        hash_content.append(self.output)
        hash_content.append(self.target)
        hash_content.extend(self.sources)
        return hashlib.sha1(''.join(hash_content)).hexdigest()
