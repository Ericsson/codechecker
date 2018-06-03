# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
This module is responsible for parsing clang-tidy output and generating plist
for the plist_parser module.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import copy
import json
import os
import plistlib
import re

from libcodechecker.logger import get_logger
from libcodechecker.report import generate_report_hash

LOG = get_logger('analyzer.tidy')


class Note(object):
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

    def __init__(self, path, line, column, message, checker,
                 code_lines=None, arrow_lines=None, fixits=None,
                 notes=None):
        super(Message, self).__init__(path, line, column, message)
        self.checker = checker
        self.code_lines = code_lines if code_lines else []
        self.arrow_lines = arrow_lines if arrow_lines else []
        self.fixits = fixits if fixits else []
        self.notes = notes if notes else []

    def __eq__(self, other):
        return super(Message, self).__eq__(other) and \
            self.checker == other.checker and \
            self.code_lines == other.code_lines and \
            self.arrow_lines == other.arrow_lines and \
            self.fixits == other.fixits and \
            self.notes == other.notes

    def __str__(self):
        return '%s, checker=%s, code_lines=%s, arrow_lines=%s, ' \
               'fixits=%s, notes=%s' % (super(Message, self).__str__(),
                                        self.checker,
                                        [str(fixed_message)
                                         for fixed_message
                                         in self.code_lines],
                                        [str(arrow_line)
                                         for arrow_line in self.arrow_lines],
                                        [str(fixit) for fixit in self.fixits],
                                        [str(note) for note in self.notes])


class OutputParser(object):
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
        r'(?P<column>\d+?):\ '
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
        r'(?P<column>\d+?):\ '
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

        with open(path, 'r') as file:
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
            line = titer.next()
            line = self._parse_code_lines(message, titer, line)
            line = self._parse_arrow_lines(message, titer, line)
            line = self._parse_fixits(message, titer, line)
            line = self._parse_notes(message, titer, line)

            return message, line
        except StopIteration:
            return message, ''

    @staticmethod
    def _parse_code_lines(message, titer, line):
        """Parses original code line."""
        while OutputParser.note_line_re.match(line) or \
                OutputParser.message_line_re.match(line) or '^' not in line:

            message_text = line
            if message_text == '':
                continue

            message.code_lines.append(Note(message.path, message.line,
                                           line.find(
                                               message_text) + 1,
                                           message_text))

            line = titer.next()
        return line

    @staticmethod
    def _parse_arrow_lines(message, titer, line):
        """Parses arrow line."""
        while OutputParser.message_line_re.match(line) is None and \
                OutputParser.note_line_re.match(line) is None and '^' in line:

            message_text = line
            if message_text == '':
                continue

            message.arrow_lines.append(Note(message.path, message.line,
                                            line.find(message_text) + 1,
                                            message_text))
            line = titer.next()
        return line

    @staticmethod
    def _parse_fixits(message, titer, line):
        """Parses fixit messages."""

        while OutputParser.message_line_re.match(line) is None and \
                OutputParser.note_line_re.match(line) is None and \
                '^' not in line:

            message_text = line.strip()

            if message_text != '':
                message.fixits.append(Note(message.path, message.line,
                                           line.find(message_text) + 1,
                                           message_text))
            line = next(titer)
        return line

    def _parse_notes(self, message, titer, line):
        """Parses note messages."""

        while OutputParser.message_line_re.match(line) is None and \
                '^' not in line:
            match = OutputParser.note_line_re.match(line)

            if match is None:
                LOG.debug("Unexpected line: %s" % line)
                return next(titer)

            message.notes.append(Note(os.path.abspath(match.group('path')),
                                      int(match.group('line')),
                                      int(match.group('column')),
                                      match.group('message').strip()))
            line = titer.next()
            line = self._parse_code_lines(message, titer, line)
        return line


class PListConverter(object):
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
            diag = PListConverter._create_diag(message, fmap, files)
            self.plist['diagnostics'].append(diag)

    @staticmethod
    def _get_checker_category(checker):
        """
        Returns the check's category.
        """

        parts = checker.split('-')
        if len(parts) == 0:
            # I don't know if it's possible.
            return 'unknown'
        else:
            return parts[0]

    @staticmethod
    def _create_diag(message, fmap, files):
        """
        Creates a new plist diagnostic from a single clang-tidy message.
        """

        diag = {}
        diag['location'] = PListConverter._create_location(message, fmap)
        diag['check_name'] = message.checker
        diag['description'] = message.message
        diag['category'] = PListConverter._get_checker_category(
            message.checker)
        diag['type'] = 'clang-tidy'
        diag['path'] = []

        PListConverter._add_fixed_code_lines(diag, message, fmap)
        PListConverter._add_notes(diag, message, fmap)

        # The original message should be the last part of the path. This is
        # displayed by quick check, and this is the main event displayed by
        # the web interface. FIXME: notes and fixits should not be events.
        diag['path'].append(PListConverter._create_event_from_note(message,
                                                                   fmap))

        diag['issue_hash_content_of_line_in_context'] \
            = generate_report_hash(diag['path'],
                                   files[diag['location']['file']],
                                   message.checker)

        return diag

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
    def _create_fixit_from_note(note, fmap):
        return {
            'kind': 'fixit',
            'location': PListConverter._create_location(note, fmap),
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
    def _add_fixed_code_lines(diag, message, fmap):
        """
        Adds fixed things as events to the diagnostics.
        """

        for original in message.code_lines:
            original_line = original.message

            for arrow_line in message.arrow_lines:

                if arrow_line.line == original.line and \
                        arrow_line.column == original.column:

                    for fixit in message.fixits:
                        message_fixit = copy.deepcopy(fixit)

                        received_fixits = fixit.message.split()

                        first_fixit_start_position = arrow_line.message.find(
                            '^')

                        first_fixit_end_position = arrow_line.message.find(
                            ' ', first_fixit_start_position)

                        second_fixit_start_position = arrow_line.message.find(
                            '~', first_fixit_end_position)

                        second_fixit_end_position = arrow_line.message.rfind(
                            '~', second_fixit_start_position) + 1

                        if len(received_fixits) == 2:
                            original_line = "".join(
                                (original_line[:second_fixit_start_position],
                                 received_fixits[1],
                                 original_line[second_fixit_end_position-1:]))

                        fixit = "".join(
                            (original_line[:first_fixit_start_position],
                             received_fixits[0],
                             original_line[first_fixit_end_position:]))

                        message_fixit.message = '%s (fixed)' % fixit.lstrip()
                        message_fixit.column = len(fixit) - len(fixit.lstrip())

                        diag['path'].append(
                            PListConverter._create_fixit_from_note(
                                message_fixit, fmap))
                        break
            break

    @staticmethod
    def _add_arrow_lines(diag, message, fmap):
        """
        Adds arrow lines as events to the diagnostics.
        """

        for arrow_line in message.arrow_lines:
            message_fixit = copy.deepcopy(arrow_line)
            message_fixit.message = '%s (fixit)' % arrow_line.message
            diag['path'].append(PListConverter._create_event_from_note(
                message_fixit, fmap))

    @staticmethod
    def _add_fixits(diag, message, fmap):
        """
        Adds fixits as events to the diagnostics.
        """

        for fixit in message.fixits:
            message_fixit = copy.deepcopy(fixit)
            message_fixit.message = '%s (fixit)' % fixit.message
            diag['path'].append(PListConverter._create_event_from_note(
                message_fixit, fmap))

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

        plistlib.writePlist(self.plist, file)

    def __str__(self):
        return str(json.dumps(self.plist, indent=4, separators=(',', ': ')))
