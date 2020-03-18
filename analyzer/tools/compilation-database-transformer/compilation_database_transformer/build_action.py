# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
""""""

import shlex


def has_flag(flag, cmd):
    """Return true if a cmd contains a flag or false if not."""
    return bool(next((x for x in cmd if x.startswith(flag)), False))


def prepend_all(flag, params):
    """
    Returns a list where all elements of "params" is prepended with the given
    flag. For example in case "flag" is -f and "params" is ['a', 'b', 'c'] the
    result is ['-f', 'a', '-f', 'b', '-f', 'c'].
    """
    result = []
    for param in params:
        result.append(flag)
        result.append(param)
    return result


class BuildAction(object):
    """
    The objects of this class hold information which is the input of the
    analyzer engines.
    """

    __slots__ = ['analyzer_options',
                 'compiler_includes',
                 'compiler_standard',
                 'analyzer_type',
                 'original_command',
                 'directory',
                 'output',
                 'lang',
                 'target',
                 'source',
                 'action_type']

    LINK = 0
    COMPILE = 1
    PREPROCESS = 2
    INFO = 3

    def __init__(self, **kwargs):
        # Filtered list of options.
        for slot in BuildAction.__slots__:
            super(BuildAction, self).__setattr__(slot, kwargs[slot])

    def __str__(self):
        # For debugging.
        return ('\nOriginal command: {0},\n'
                'Analyzer type: {1},\n Analyzer options: {2},\n'
                'Directory: {3},\nOutput: {4},\nLang: {5},\nTarget: {6},\n'
                'Source: {7}'). \
            format(self.original_command,
                   self.analyzer_type, self.analyzer_options,
                   self.directory, self.output, self.lang, self.target,
                   self.source)

    def __setattr__(self, attr, value):
        if hasattr(self, attr) and getattr(self, attr) != value:
            raise AttributeError("BuildAction is immutable")
        super(BuildAction, self).__setattr__(attr, value)

    def __eq__(self, other):
        return other.original_command == self.original_command

    def to_dict(self):
        """Reverting to original compilation database
        record for JSON conversion.
        """
        return {"directory": self.directory,
                "command": self.original_command,
                "file": self.source}

    def __command_str(self):
        compiler_binary = shlex.split(self.original_command)[0]
        analyzer_cmd = [compiler_binary]
        compile_lang = self.lang
        if not has_flag('-x', self.original_command):
            analyzer_cmd.extend(['-x', compile_lang])

        if (not has_flag('--target', self.original_command) and
                self.target.get(compile_lang, "") != ""):
            analyzer_cmd.append("--target=" + self.target.get(compile_lang))

        if (not has_flag('-std', self.original_command) and
                self.compiler_standard.get(compile_lang, "") != ""):
            analyzer_cmd.append(self.compiler_standard[compile_lang])

        analyzer_cmd.extend(self.analyzer_options)

        analyzer_cmd.extend(prepend_all(
            '-isystem',
            self.compiler_includes[compile_lang]))

        analyzer_cmd.append(self.source)

        analyzer_cmd.append('-o ' + self.output)

        return ' '.join(analyzer_cmd)

    def to_analyzer_dict(self):
        """Convert to a dict containing the parsed compile command, and
        prepared to be used in an analyzerinvocation.
        """
        return {"directory": self.directory,
                "command": self.__command_str(),
                "file": self.source}

    def __hash__(self):
        """
        If the compilation database contains the same compilation action
        multiple times it should be checked only once.
        Use this key to compare compilation commands for the analysis.
        """
        hash_content = []
        hash_content.extend(self.analyzer_options)
        hash_content.append(str(self.analyzer_type))
        hash_content.append(self.target[self.lang])
        hash_content.append(self.source)
        return hash(''.join(hash_content))

    def with_attr(self, attr, value):
        details = {key: getattr(self, key) for key in BuildAction.__slots__}
        details[attr] = value
        return BuildAction(**details)
