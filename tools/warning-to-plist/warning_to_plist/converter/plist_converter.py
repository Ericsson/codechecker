#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from abc import ABCMeta, abstractmethod
import copy
import json
import plistlib

from .report import generate_report_hash


class PlistConverter(object):
    """ Warning messages to plist converter. """

    __metaclass__ = ABCMeta

    def __init__(self):
        self.plist = {
            'files': [],
            'diagnostics': []
        }

    @abstractmethod
    def parse_messages(self, output):
        """ Parse the given output. """
        raise NotImplementedError("Subclasses should implement this!")

    def add_messages(self, messages):
        """ Adds the given messages to the plist. """
        self._add_diagnostics(messages, self.plist['files'])

    def write_to_file(self, path):
        """ Writes out the plist XML to the given path. """
        with open(path, 'wb') as file:
            self.write(file)

    def write(self, file):
        """ Writes out the plist XML using the given file object. """
        plistlib.writePlist(self.plist, file)

    def _create_location(self, msg, fmap):
        """ Create a location section from the message. """
        return {'line': msg.line,
                'col': msg.column,
                'file': fmap[msg.path]}

    def _create_event(self, msg, fmap):
        """ Create an event from the given message. """
        return {'kind': 'event',
                'location': self._create_location(msg, fmap),
                'depth': 0,
                'message': msg.message}

    def _create_note(self, msg, fmap):
        """ Create a note from the given message. """
        return {'kind': 'note',
                'location': self._create_location(msg, fmap),
                'depth': 0,
                'message': msg.message}

    def _create_edge(self, start_msg, end_msg, fmap):
        """ Create an edge between the start and end messages. """
        start_loc = self._create_location(start_msg, fmap)
        end_loc = self._create_location(end_msg, fmap)
        return {'start': [start_loc, start_loc],
                'end': [end_loc, end_loc]}

    def _add_diagnostics(self, messages, files):
        """ Adds the messages to the plist as diagnostics. """
        fmap = self._add_files_from_messages(messages)
        for message in messages:
            diag = self._create_diag(message, fmap, files)
            self.plist['diagnostics'].append(diag)

    def _add_files_from_message(self, message, fmap):
        """ Add new file from the given message. """
        try:
            idx = self.plist['files'].index(message.path)
            fmap[message.path] = idx
        except ValueError:
            fmap[message.path] = len(self.plist['files'])
            self.plist['files'].append(message.path)

    def _add_files_from_messages(self, messages):
        """ Add new file from the given messages.

        Adds the new files from the given message array to the plist's "files"
        key, and returns a path to file index dictionary.
        """
        fmap = {}
        for message in messages:
            self._add_files_from_message(message, fmap)

            # Collect file paths from the events.
            for nt in message.events:
                self._add_files_from_message(nt, fmap)

        return fmap

    @abstractmethod
    def _get_checker_category(self, checker):
        """ Returns the check's category."""
        raise NotImplementedError("Subclasses should implement this!")

    @abstractmethod
    def _get_analyzer_type(self):
        """ Returns the analyzer type. """
        raise NotImplementedError("Subclasses should implement this!")

    def _create_diag(self, message, fmap, files):
        """ Creates a new plist diagnostic from the given message. """
        diag = {'location': self._create_location(message, fmap),
                'check_name': message.checker,
                'description': message.message,
                'category': self._get_checker_category(message.checker),
                'type': self._get_analyzer_type(),
                'path': [],
                'notes': []}

        self.__add_fixits(diag, message, fmap)
        self.__add_events(diag, message, fmap)
        self.__add_notes(diag, message, fmap)

        # The original message should be the last part of the path. This is
        # displayed by quick check, and this is the main event displayed by
        # the web interface. FIXME: notes and fixits should not be events.
        diag['path'].append(self._create_event(message, fmap))

        diag['issue_hash_content_of_line_in_context'] \
            = generate_report_hash(diag,
                                   files[diag['location']['file']])

        return diag

    def __add_fixits(self, diag, message, fmap):
        """ Adds fixits as events to the diagnostics. """
        for fixit in message.fixits:
            mf = copy.deepcopy(fixit)
            mf.message = '%s (fixit)' % fixit.message
            diag['path'].append(self._create_event(mf, fmap))

    def __add_notes(self, diag, message, fmap):
        """ Adds notes to the diagnostics. """
        for note in message.notes:
            diag['notes'].append(self._create_note(note, fmap))

    def __add_events(self, diag, message, fmap):
        """ Adds events to the diagnostics.

        It also creates edges between the events.
        """
        edges = []
        last = None
        for event in message.events:
            if last is not None:
                edges.append(self._create_edge(last, event, fmap))

            diag['path'].append(self._create_event(event, fmap))
            last = event

        # Add control items only if there is any.
        if edges:
            diag['path'].append({'kind': 'control', 'edges': edges})

    def __str__(self):
        return str(json.dumps(self.plist, indent=4, separators=(',', ': ')))
