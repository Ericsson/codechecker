# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""""""


class BuildAction:
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
                 'arch',
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
        return {"command": self.original_command,
                "directory": self.directory,
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
        hash_content.append(self.target)
        hash_content.append(self.source)
        return hash(''.join(hash_content))

    def with_attr(self, attr, value):
        details = {key: getattr(self, key) for key in BuildAction.__slots__}
        details[attr] = value
        return BuildAction(**details)
