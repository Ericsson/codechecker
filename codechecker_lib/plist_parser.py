# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
""""""

# FIXME: This file contains some workarounds.
# Remove them as soon as a proper clang version comes out.

import plistlib
from xml.parsers.expat import ExpatError

from codechecker_lib import logger
from . import plist_helper

LOG = logger.get_new_logger('PLIST_PARSER')


class GenericEquality(object):

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)


# -----------------------------------------------------------------------------
class Position(GenericEquality):

    """Represent a postion."""

    def __init__(self, x, y, f):
        self.line = x
        self.col = y
        self.file_path = f


# -----------------------------------------------------------------------------
class Range(GenericEquality):

    """Represent a location in the bug path."""

    def __init__(self, start_pos, end_pos, msg=''):
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.msg = msg


# -----------------------------------------------------------------------------
def make_position(pos_map, files):
    return Position(pos_map.line, pos_map.col, files[pos_map.file])


# -----------------------------------------------------------------------------
def make_range(array, files):
    if len(array) == 2:
        start = make_position(array[0], files)
        end = make_position(array[1], files)
        return Range(start, end)


# -----------------------------------------------------------------------------
class Bug(object):

    """The bug with all information, it include bugpath too."""

    def __init__(self, file, from_pos, until_pos=None, msg=None, category=None,
                 type=None, hash_value=''):
        self.file_path = file
        self.msg = msg
        self._paths = []
        self._events = []
        self.hash_value = hash_value

        if not until_pos:
            until_pos = from_pos

        (self.from_line, self.from_col) = from_pos
        (self.until_line, self.until_col) = until_pos

    def paths(self):
        return self._paths

    def events(self):
        return self._events

    def add_to_path(self, new_range):
        self._paths.append(new_range)

    def add_to_events(self, new_range):
        self._events.append(new_range)

    def get_last_path(self):
        return self._paths[-1] if len(self._paths) > 0 else None

    def get_last_event(self):
        return self._events[-1] if len(self._events) > 0 else None


# -----------------------------------------------------------------------------
def parse_plist(path):
    """
    Parse the plist file.
    """
    bugs = []
    files = []
    try:
        plist = plistlib.readPlist(path)

        files = plist['files']

        for diag in plist['diagnostics']:
            current = Bug(files[diag['location']['file']],
                          (diag['location']['line'], diag['location']['col']))

            for item in diag['path']:
                if item['kind'] == 'event':
                    message = item['message']
                    if 'ranges' in item:
                        for arr in item['ranges']:
                            source_range = make_range(arr, files)
                            source_range.msg = message
                            current.add_to_events(source_range)
                    else:
                        location = make_position(item['location'], files)
                        source_range = Range(location, location, message)
                        source_range.msg = message
                        current.add_to_events(source_range)

                elif item['kind'] == 'control':
                    for edge in item['edges']:
                        start = make_range(edge.start, files)
                        end = make_range(edge.end, files)

                        if start != current.get_last_path():
                            current.add_to_path(start)

                        current.add_to_path(end)

            current.msg = diag['description']
            current.category = diag['category']
            current.type = diag['type']

            try:
                current.checker_name = diag['check_name']
            except KeyError as kerr:
                LOG.debug("Check name wasn't found in the plist file. "
                          "Read the user guide!")
                current.checker_name = plist_helper.get_check_name(current.msg)
                LOG.debug('Guessed check name: ' + current.checker_name)

            try:
                current.hash_value = \
                    diag['issue_hash_content_of_line_in_context']
            except KeyError as kerr:
                # Hash was not found.
                # Generate some hash for older clang versions.
                LOG.debug(kerr)
                LOG.debug("Hash value wasn't found in the plist file. "
                          "Read the user guide!")
                current.hash_value = plist_helper.gen_bug_hash(current)

            bugs.append(current)

    except ExpatError as err:
        LOG.debug('Failed to process plist file: ' + path)
        LOG.debug(err)
    finally:
        return files, bugs
