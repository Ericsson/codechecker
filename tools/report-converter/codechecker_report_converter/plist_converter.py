# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


from abc import ABCMeta
import copy
import json


class PlistConverter(metaclass=ABCMeta):
    """ Warning messages to plist converter. """

    def __init__(self, tool_name):
        self.tool_name = tool_name
        self.path_to_plist = {}

    def get_plist_results(self):
        """ Returns a list of plist results. """
        return list(self.path_to_plist.values())

    def add_messages(self, messages):
        """ Adds the given messages to the plist. """
        self._add_diagnostics(messages)

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

    def _add_diagnostics(self, messages):
        """ Adds the messages to the plist as diagnostics. """
        self._add_files_from_messages(messages)
        for message in messages:
            plist_data = self.path_to_plist[message.path]
            diag = self._create_diag(message, plist_data['files'])
            plist_data['diagnostics'].append(diag)

    def _add_files_from_message(self, message, plist_data):
        """ Add new file from the given message. """
        try:
            plist_data['files'].index(message.path)
        except ValueError:
            plist_data['files'].append(message.path)

    def _add_files_from_messages(self, messages):
        """ Add new file from the given messages.

        Adds the new files from the given message array to the plist's "files"
        key, and returns a path to file index dictionary.
        """
        for message in messages:
            if message.path not in self.path_to_plist:
                self.path_to_plist[message.path] = {
                    'files': [],
                    'diagnostics': []}

            plist_data = self.path_to_plist[message.path]

            self._add_files_from_message(message, plist_data)

            # Collect file paths from the events.
            for nt in message.events:
                self._add_files_from_message(nt, plist_data)

    def _get_checker_category(self, checker):
        """ Returns the check's category."""
        return 'unknown'

    def _get_analyzer_type(self):
        """ Returns the analyzer type. """
        return self.tool_name

    def _create_diag(self, message, files):
        """ Creates a new plist diagnostic from the given message. """
        fmap = {files[i]: i for i in range(0, len(files))}
        checker_name = message.checker if message.checker else self.tool_name
        diag = {'location': self._create_location(message, fmap),
                'check_name': checker_name,
                'description': message.message,
                'category': self._get_checker_category(message.checker),
                'type': self._get_analyzer_type(),
                'path': []}

        self.__add_fixits(diag, message, fmap)
        self.__add_events(diag, message, fmap)
        self.__add_notes(diag, message, fmap)

        # The original message should be the last part of the path. This is
        # displayed by quick check, and this is the main event displayed by
        # the web interface. FIXME: notes and fixits should not be events.
        diag['path'].append(self._create_event(message, fmap))

        return diag

    def __add_fixits(self, diag, message, fmap):
        """ Adds fixits as events to the diagnostics. """
        for fixit in message.fixits:
            mf = copy.deepcopy(fixit)
            mf.message = '%s (fixit)' % fixit.message
            diag['path'].append(self._create_event(mf, fmap))

    def __add_notes(self, diag, message, fmap):
        """ Adds notes to the diagnostics. """
        if not message.notes:
            return

        diag['notes'] = [self._create_note(n, fmap) for n in message.notes]

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
        return str(json.dumps(self.path_to_plist,
                              indent=4,
                              separators=(',', ': ')))
