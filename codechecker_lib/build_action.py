# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
''''''

# -----------------------------------------------------------------------------
class BuildAction(object):
    def __init__(self, build_action_id=0):
        self._id = build_action_id
        self._analyzer_options = []
        self._original_command = ''
        self._directory = ''
        self._output = ''
        self._lang = None
        self._target = ''
        self._source_count = 0
        self._sources = []
        self._skip = True

    def __str__(self):
        # for debugging
        return ('Id: {0} ,\nOriginal command: {1},\nAnalyzer options: {2},\n'
                'Directory: {3},\nOutput: {4},\nLang: {5},\nTarget: {6},\n'
                'Source count {7},\nSources: {8}').\
                    format(self._id, self._original_command, self._analyzer_options,
                           self._directory, self._output, self._lang, self._target,
                           self._source_count, self._sources)

    @property
    def id(self):
        return self._id

    @property
    def analyzer_options(self):
        return self._analyzer_options

    @analyzer_options.setter
    def analyzer_options(self, value):
        '''A filtered compile arguments which will be forwarded to the analyzer.'''
        self._analyzer_options = value

    @property
    def original_command(self):
        return self._original_command

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
