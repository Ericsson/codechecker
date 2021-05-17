# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


from abc import ABCMeta


def get_next(it):
    """ Returns the next item from the iterator or return an empty string. """
    try:
        return next(it)
    except StopIteration:
        return ''


class Event:
    """ Represents an event message. """

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
        return 'path={0}, line={1}, column={2}, message={3}'.format(
            self.path, self.line, self.column, self.message)


class Message(Event):
    """ Represents a message with an optional event, fixit and note messages.

    This will be a diagnostic section in the plist which represents a report.
    """

    def __init__(self, path, line, column, message, checker, events=None,
                 notes=None, fixits=None):
        super(Message, self).__init__(path, line, column, message)
        self.checker = checker
        self.events = events if events else []
        self.notes = notes if notes else []
        self.fixits = fixits if fixits else []

    def __eq__(self, other):
        return super(Message, self).__eq__(other) and \
            self.checker == other.checker and \
            self.events == other.events and \
            self.notes == other.notes and \
            self.fixits == other.fixits

    def __str__(self):
        return '%s, checker=%s, events=%s, notes=%s, fixits=%s' % \
               (super(Message, self).__str__(), self.checker,
                [str(event) for event in self.events],
                [str(note) for note in self.notes],
                [str(fixit) for fixit in self.fixits])


class BaseParser(metaclass=ABCMeta):
    """ Warning message parser. """

    def __init__(self):
        self.messages = []

    def parse_messages_from_file(self, path):
        """ Parse output dump (redirected output). """
        with open(path, 'r', encoding="utf-8", errors="ignore") as file:
            return self.parse_messages(file)

    def parse_messages(self, lines):
        """ Parse the given output. """
        it = iter(lines)
        try:
            next_line = next(it)
            while True:
                message, next_line = self.parse_message(it, next_line)
                if message:
                    self.messages.append(message)
        except StopIteration:
            pass

        return self.messages

    def parse_message(self, it, line):
        """ Parse the given line. """
        raise NotImplementedError("Subclasses should implement this!")
