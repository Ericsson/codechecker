# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
This module is responsible for parsing clang-tidy output and generating plist
for the plist_parser module.
"""


import copy
import json
import os
import plistlib
import re

from codechecker_common.logger import get_logger
from codechecker_report_hash.hash import get_report_hash, HashType

LOG = get_logger('analyzer.tidy')


class Note:
    """
    Represents a note and also this is the base class of Message.
    """

    def __init__(self, path, line, column, message):
        self.path = path
        self.line = line
        self.column = column
        self.message = message

    def __eq__(self, other):
        return self.path == other.path and \
            self.line == other.line and \
            self.column == other.column and \
            self.message == other.message

    def __str__(self):
        return 'path=%s, line=%d, column=%s, message=%s' % \
               (self.path, self.line, self.column, self.message)


class Message(Note):
    """
    Represents a clang-tidy message with an optional fixit message.
    """

    def __init__(self, path, line, column, message, checker, fixits=None,
                 notes=None):
        super(Message, self).__init__(path, line, column, message)
        self.checker = checker
        self.fixits = fixits if fixits else []
        self.notes = notes if notes else []

    def __eq__(self, other):
        return super(Message, self).__eq__(other) and \
            self.checker == other.checker and \
            self.fixits == other.fixits and \
            self.notes == other.notes

    def __str__(self):
        return '%s, checker=%s, fixits=%s, notes=%s' % \
               (super(Message, self).__str__(), self.checker,
                [str(fixit) for fixit in self.fixits],
                [str(note) for note in self.notes])


class OutputParser:
    """
    Parser for clang-tidy console output.
    """

    # Regex for parsing a clang-tidy message.
    message_line_re = re.compile(
        # File path followed by a ':'.
        r'^(?P<path>[\S ]+?):'
        # Line number followed by a ':'.
        r'(?P<line>\d+?):'
        # Column number followed by a ':' and a space.
        r'(?P<column>\d+?): '
        # Severity followed by a ':'.
        r'(?P<severity>(error|warning)):'
        # Checker message.
        r'(?P<message>[\S \t]+)\s*'
        # Checker name.
        r'\[(?P<checker>.*)\]')

    # Matches a note.
    note_line_re = re.compile(
        # File path followed by a ':'.
        r'^(?P<path>[\S ]+?):'
        # Line number followed by a ':'.
        r'(?P<line>\d+?):'
        # Column number followed by a ':' and a space.
        r'(?P<column>\d+?): '
        # Severity == note.
        r'note:'
        # Checker message.
        r'(?P<message>.*)')

    def __init__(self):
        self.messages = []

    def parse_messages_from_file(self, path):
        """
        Parse clang-tidy output dump (redirected output).
        """

        with open(path, 'r', encoding="utf-8", errors="ignore") as file:
            return self.parse_messages(file)

    def parse_messages(self, tidy_out):
        """
        Parse the given clang-tidy output. This method calls iter(tidy_out).
        The iterator should return lines.

        Parameters:
            tidy_out: something iterable (e.g.: a file object)
        """

        titer = iter(tidy_out)
        try:
            next_line = next(titer)
            while True:
                message, next_line = self._parse_message(titer, next_line)
                if message is not None:
                    self.messages.append(message)
        except StopIteration:
            pass

        return self.messages

    def _parse_message(self, titer, line):
        """
        Parse the given line. Returns a (message, next_line) pair or throws a
        StopIteration. The message could be None.

        Parameters:
            titer: clang-tidy output iterator
            line: the current line
        """

        match = OutputParser.message_line_re.match(line)
        if match is None:
            return None, next(titer)

        message = Message(
            os.path.abspath(match.group('path')),
            int(match.group('line')),
            int(match.group('column')),
            match.group('message').strip(),
            match.group('checker').strip())

        try:
            line = next(titer)
            line = self._parse_code(message, titer, line)
            line = self._parse_fixits(message, titer, line)
            line = self._parse_notes(message, titer, line)

            return message, line
        except StopIteration:
            return message, ''

    @staticmethod
    def _parse_code(message, titer, line):
        # Eat code line.
        if OutputParser.note_line_re.match(line) or \
                OutputParser.message_line_re.match(line):
            LOG.debug("Unexpected line: %s. Expected a code line!", line)
            return line

        # Eat arrow line.
        # FIXME: range support?
        line = next(titer)
        if '^' not in line:
            LOG.debug("Unexpected line: %s. Expected an arrow line!", line)
            return line
        return next(titer)

    @staticmethod
    def _parse_fixits(message, titer, line):
        """Parses fixit messages."""

        while OutputParser.message_line_re.match(line) is None and \
                OutputParser.note_line_re.match(line) is None:
            message_text = line.strip()

            if message_text != '':
                message.fixits.append(Note(message.path, message.line,
                                           line.find(message_text) + 1,
                                           message_text))
            line = next(titer)
        return line

    def _parse_notes(self, message, titer, line):
        """Parses note messages."""

        while OutputParser.message_line_re.match(line) is None:
            match = OutputParser.note_line_re.match(line)
            if match is None:
                LOG.debug("Unexpected line: %s", line)
                return next(titer)

            message.notes.append(Note(os.path.abspath(match.group('path')),
                                      int(match.group('line')),
                                      int(match.group('column')),
                                      match.group('message').strip()))
            line = next(titer)
            line = self._parse_code(message, titer, line)
        return line


class PListConverter:
    """
    Clang-tidy messages to plist converter.
    """

    def __init__(self):
        self.plist = {
            'files': [],
            'diagnostics': []
        }

    def _add_files_from_messages(self, messages):
        """
        Adds the new files from the given message array to the plist's "files"
        key, and returns a path to file index dictionary.
        """

        fmap = {}
        for message in messages:
            try:
                # This file is already in the plist.
                idx = self.plist['files'].index(message.path)
                fmap[message.path] = idx
            except ValueError:
                # New file.
                fmap[message.path] = len(self.plist['files'])
                self.plist['files'].append(message.path)

            # Collect file paths from the message notes.
            for nt in message.notes:
                try:
                    # This file is already in the plist.
                    idx = self.plist['files'].index(nt.path)
                    fmap[nt.path] = idx
                except ValueError:
                    # New file.
                    fmap[nt.path] = len(self.plist['files'])
                    self.plist['files'].append(nt.path)

        return fmap

    def _add_diagnostics(self, messages, files):
        """
        Adds the messages to the plist as diagnostics.
        """

        fmap = self._add_files_from_messages(messages)
        for message in messages:
            diagnostics = PListConverter._create_diags(message, fmap, files)
            self.plist['diagnostics'].extend(diagnostics)

    @staticmethod
    def _get_checker_category(checker):
        """
        Returns the check's category.
        """

        parts = checker.split('-')
        if not parts:
            # I don't know if it's possible.
            return 'unknown'
        else:
            return parts[0]

    @staticmethod
    def _create_diags(message, fmap, files):
        """
        Creates new plist diagnostics from a single clang-tidy message.
        """
        diagnostics = []

        checker_names = sorted(message.checker.split(','))
        for checker_name in checker_names:
            diag = {'location': PListConverter._create_location(message, fmap),
                    'check_name': checker_name,
                    'description': message.message,
                    'category': PListConverter._get_checker_category(
                        checker_name),
                    'type': 'clang-tidy',
                    'path': []}

            PListConverter._add_fixits(diag, message, fmap)
            PListConverter._add_notes(diag, message, fmap)

            # The original message should be the last part of the path. This is
            # displayed by quick check, and this is the main event displayed by
            # the web interface. FIXME: notes and fixits should not be events.
            diag['path'].append(PListConverter._create_event_from_note(message,
                                                                       fmap))

            source_file = files[diag['location']['file']]
            diag['issue_hash_content_of_line_in_context'] \
                = get_report_hash(diag, source_file, HashType.PATH_SENSITIVE)

            diagnostics.append(diag)

        return diagnostics

    @staticmethod
    def _create_location(note, fmap):
        return {
            'line': note.line,
            'col': note.column,
            'file': fmap[note.path]
        }

    @staticmethod
    def _create_event_from_note(note, fmap):
        return {
            'kind': 'event',
            'location': PListConverter._create_location(note, fmap),
            'depth': 0,  # I don't know WTF is this.
            'message': note.message
        }

    @staticmethod
    def _create_edge(start_note, end_note, fmap):
        start_loc = PListConverter._create_location(start_note, fmap)
        end_loc = PListConverter._create_location(end_note, fmap)
        return {
            'start': [start_loc, start_loc],
            'end': [end_loc, end_loc]
        }

    @staticmethod
    def _add_fixits(diag, message, fmap):
        """
        Adds fixits as events to the diagnostics.
        """

        for fixit in message.fixits:
            mf = copy.deepcopy(fixit)
            mf.message = '%s (fixit)' % fixit.message
            diag['path'].append(PListConverter._create_event_from_note(
                mf, fmap))

    @staticmethod
    def _add_notes(diag, message, fmap):
        """
        Adds notes as events to the diagnostics. It also creates edges between
        the notes.
        """

        edges = []
        last = None
        for note in message.notes:
            if last is not None:
                edges.append(PListConverter._create_edge(last, note, fmap))
            diag['path'].append(PListConverter._create_event_from_note(
                note, fmap))
            last = note

        # Add control items only if there is any.
        if edges:
            diag['path'].append({
                'kind': 'control',
                'edges': edges
            })

    def add_messages(self, messages):
        """
        Adds the given clang-tidy messages to the plist.
        """

        self._add_diagnostics(messages, self.plist['files'])

    def write_to_file(self, path):
        """
        Writes out the plist XML to the given path.
        """

        with open(path, 'wb') as file:
            self.write(file)

    def write(self, file):
        """
        Writes out the plist XML using the given file object.
        """
        plistlib.dump(self.plist, file)

    def __str__(self):
        return str(json.dumps(self.plist, indent=4, separators=(',', ': ')))
