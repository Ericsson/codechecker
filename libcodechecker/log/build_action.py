# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
""""""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import hashlib


class BuildAction(object):
    LINK = 0
    COMPILE = 1
    PREPROCESS = 2
    INFO = 3

    def __init__(self, build_action_id=0):
        self._id = build_action_id
        # Filtered list of options.
        self.analyzer_options = []
        self.compiler_includes = []
        self.analyzer_type = -1
        self._original_command = ''
        self.directory = ''
        self.output = ''
        self.lang = None
        self.target = ''
        self.sources = []

    def __str__(self):
        # For debugging.
        return ('Id: {0} ,\nOriginal command: {1},\n'
                'Analyzer type: {2},\n Analyzer options: {3},\n'
                'Directory: {4},\nOutput: {5},\nLang: {6},\nTarget: {7},\n'
                'Sources: {8}'). \
            format(self._id, self._original_command,
                   self.analyzer_type, self.analyzer_options,
                   self.directory, self.output, self.lang, self.target,
                   self.sources)

    @property
    def id(self):
        return self._id

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
        hash_content.append(str(self.analyzer_type))
        hash_content.append(self.target)
        hash_content.extend(self.sources)
        return hashlib.sha1(''.join(hash_content)).hexdigest()
