# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Parsers for the analyzer output formats (plist ...) should create this
Report which will be stored.

Multiple bug identification hash-es can be generated.
All hash generation algorithms should be documented and implemented here.

"""
import hashlib
import linecache
import os

from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('REPORT')


class Report(object):
    """
    The report with all information parsed from the analyzers output files.
    One reports includes multiple diagnostic sections.

    The diagnostic sections can build up a bug path or can be standalone.

    There should be at least a main diagnostic section in each report.

    There are multiple ids to identify a report.

    report_id
      * Should be unique it is a combination of the bug hash and the path hash.

    report_hash
      * A unique identifier should be generate by the analyzer if not this
        module generates an identifier based on the bug path if available.

    obsolate_report_hash
      * There is already an algorithm to generate a unique identifier which
        should be changed and not used after v6.0.

    """

    def __init__(self, checker_name, report_hash=None,
                 category=None, type=None):

        self.checker_name = checker_name
        self.category = category
        self.type = type
        self.__hash_value = report_hash

        # The main diag section for the report.
        self.__main_section = None
        # Diag sections without a path.
        self.__diag_sections = []
        # An optional bug path.
        self.__bug_path = None

    def diag_sections(self):
        return self.__diag_sections

    @property
    def file_path(self):
        self.__main_section.start_range.begin.file_path

    @property
    def main_section(self):
        """
        Main section after v6.0.
        """
        return self.__main_section

    @main_section.setter
    def main_section(self, main_section):
        self.__main_section = main_section

    @property
    def obsolate_main_section(self):
        """
        Main section before v6.0.
        """
        return self.__bug_path.get_diag_sections()[-1]

    def add_diag_section(self, section):
        self.__diag_sections.append(section)

    def set_path(self, bug_path):
        self.__bug_path = bug_path

    def get_path(self):
        return self.__bug_path

    def report_id(self):
        return self.hash_value + "||" + self.__bug_path.path_hash

    @property
    def report_hash(self):
        """
        If hash value is not set in the analyzers output generate a new.
        """
        if not self.__hash_value:
            # NOTE  uses a different algorithm compared to obsolate hash.
            self.__hash_value = self.__gen_report_hash()

        return self.__hash_value

    def events(self):
        # TODO: FOR STORAGE BACKWARD COMPATIBILITY REMOVE AFTER v6.0
        return [x for x in self.__bug_path.get_diag_sections() if
                x.kind == "event"]

    def paths(self):
        # TODO: FOR STORAGE BACKWARD COMPATIBILITY REMOVE AFTER v6.0
        return [x for x in self.__bug_path.get_diag_sections() if
                x.kind == "control"]

    @property
    def hash_value(self):
        # TODO: FOR STORAGE BACKWARD COMPATIBILITY REMOVE AFTER v6.0
        hash = self.__hash_value
        if not hash:
            hash = self.__obsolate_hash()
        return hash

    def __obsolate_hash(self):
        """
        !!! Compatible with the old hash before v6.0

        Keep this until needed for transformation tools from the old
        hash to the new hash.

        Hash generation algoritm for older plist versions where no
        issue hash was generated or for the plists generated
        from clang-tidy where the issue hash generation feature
        is still missing.

        As the main diagnositc section the last element from the
        bug path is used.

        Hash content:
         * file_name from the main diag section.
         * checker name
         * checker message
         * line content from the source file if can be read up
         * column numbers from the main diag section
         * range column numbers only from the control diag sections if
           column number in the range is not the same as the previous
           control diag section number in the bug path

        """
        # The last diag section from the bug path used as a main
        # diagnostic section.
        mds = self.__bug_path.get_diag_sections()[-1]

        source_file = mds.location.file_path
        source_line = mds.location.line

        from_col = mds.location.col
        until_col = mds.location.col

        line_content = linecache.getline(source_file, source_line)

        if line_content == '' and not os.path.isfile(source_file):
            LOG.debug("Failed to generate report hash.")
            LOG.debug('%s does not exists!' % source_file)

        file_name = os.path.basename(source_file)
        msg = mds.msg

        hash_content = [file_name,
                        self.checker_name,
                        msg,
                        line_content,
                        str(from_col),
                        str(until_col)]

        diag_sections = self.__bug_path.get_diag_sections()

        ctrl_sections = [x for x in diag_sections if x.kind == "control"]

        for i, diag_section in enumerate(ctrl_sections):
            ds_start_range = diag_section.start_range
            if i > 0:
                prev = ctrl_sections[i-1]
                if ds_start_range.begin != prev.end_range.begin and \
                        ds_start_range.end != prev.end_range.end:
                    hash_content.append(str(ds_start_range.begin.col))
                    hash_content.append(str(ds_start_range.end.col))
            else:
                hash_content.append(str(ds_start_range.begin.col))
                hash_content.append(str(ds_start_range.end.col))

            hash_content.append(str(diag_section.end_range.begin.col))
            hash_content.append(str(diag_section.end_range.end.col))

        string_to_hash = '|||'.join(hash_content)

        return hashlib.md5(string_to_hash.encode()).hexdigest()

    def __gen_report_hash(self):
        """
        Generate a report hash if the analyzer failed to generate
        or not supported by the analyzer.
        """
        # TODO: REVIEW IS NEEDED WHAT TO INCLUDE IN THE HASH.
        # NOTE: DO NOT USE UNTIL COMMENT IS REMOVED!

        source_file = self.main_section.start_range.begin.file_path
        source_line = self.main_section.start_range.begin.line

        from_col = self.main_section.start_range.begin.col
        until_col = self.main_section.end_range.begin.col

        from_col = self.main_section.location.col
        until_col = self.main_section.location.col

        line_content = linecache.getline(source_file, source_line)

        if line_content == '' and not os.path.isfile(source_file):
            LOG.error("Failed to generate report hash.")
            LOG.error('%s does not exists!' % source_file)

        file_name = os.path.basename(source_file)
        msg = self.main_section.msg

        # Add the main diag section for the hash content.
        hash_content = [file_name,
                        self.checker_name,
                        msg,
                        line_content,
                        str(from_col),
                        str(until_col)]

        diag_sections = self.__bug_path.get_diag_sections()

        # Add only the control diag section column numbers to the hash content.
        ctrl_sections = [x for x in diag_sections if x.kind == "control"]

        for diag_section in ctrl_sections:
            hash_content.append(str(diag_section.start_range.begin.col))
            hash_content.append(str(diag_section.start_range.end.col))
            hash_content.append(str(diag_section.end_range.begin.col))
            hash_content.append(str(diag_section.end_range.end.col))

        string_to_hash = '|||'.join(hash_content)

        bug_hash = hashlib.md5(string_to_hash.encode()).hexdigest()
        return bug_hash


class GenericEquality(object):

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)


class Position(GenericEquality):
    """
    Represent a postion in a source file.
    """

    def __init__(self, line, col, filepath):
        self.line = line
        self.col = col
        self.file_path = filepath

    def __str__(self):
        msg = "@"+str(self.line)+":"+str(self.col)+"::"+str(self.file_path)
        return msg


class Range(object):
    """
    Two positions build a range.
    """
    def __init__(self, begin, end=None):
        self.__begin = begin
        if end:
            self.__end = end
        else:
            self.__end = begin

    def __str__(self):
        msg = "["+str(self.__begin) + "][" + str(self.__end)+"]"
        return msg

    @property
    def begin(self):
        return self.__begin

    @property
    def end(self):
        return self.__end


class BugPath(object):
    """
    Represents a bug path which contains multiple DiagSections.
    The order of the diagnostic sections in the bug path matters, and
    needed for the storage in the database and for the UI to
    render arrows properly.
    """
    def __init__(self, diag_sections):
        self.__diag_sections = diag_sections
        self.__path_length = 0
        # Initialize path positions.
        for i, ds in enumerate(self.__diag_sections):
            self.__diag_sections[i].path_position = i

    def get_diag_sections(self):
        return self.__diag_sections

    def len(self):
        """
        Contains all the control and event diag sections!
        """
        return len(self.__diag_sections)

    @property
    def path_hash(self):
        """
        Generate a unique id for a bug path.

        * Used to identify a bug path if the report_hash is not unique enough.
        * It is possible that the same hash is generated for different reports
          where the bug paths are different to identify these cases a
          separate path hash is generated (starts in separate cpp files but
          ends in the same header).
        """
        # TODO: Review hash generation method this is just an initial version.
        # Hash is generated now based on columm numbers from the diag sections
        # in a bug path.
        # At least one event should be in the bug path.
        # NOTE: Events might only have only a location and
        # no range information.
        if not self.__path_hash:
            path = ""
            for ds in self.__diag_sections:
                path += str(ds.start_range.begin.col) + \
                    str(ds.end_range.begin.col) + \
                    ds.msg + ds.start_range.begin.file_path
            self.__path_length = hashlib.sha1(path).hexdigest()

        return self.__path_hash


class DiagSection(GenericEquality):
    """
    Diagnostic section can have a start and an end position.
    If position_in_path is set this section belongs to a BugPath.
    It is possible that a DiagSection is a standalone "message" or
    "warning" by the analyzer and does not belong to BugPath.

    See storage thrift api desctiption for kinds.
    """

    def __init__(self, kind='', msg=''):

        self.__start_range = None
        self.__end_range = None
        self.__msg = msg
        self.__extended_msg = ''
        self.__kind = kind

        # One Position.
        self.__location = None  # Optional in some cases only range is
        # available

        # Position in the path is just and integer if
        # not set DiagSection is not part of a path.
        self.__position_in_path = None

    @property
    def kind(self):
        return self.__kind

    @property
    def start_range(self):
        return self.__start_range

    @start_range.setter
    def start_range(self, range):
        self.__start_range = range

    @property
    def end_range(self):
        return self.__end_range

    @end_range.setter
    def end_range(self, range):
        self.__end_range = range

    @property
    def path_position(self):
        return self.__position_in_path

    @path_position.setter
    def path_position(self, position):
        self.__position_in_path = position

    @property
    def msg(self):
        return self.__msg

    @property
    def extended_msg(self):
        return self.__extended_msg

    @extended_msg.setter
    def extended_msg(self, msg):
        self.__extended_msg = msg

    @property
    def location(self):
        return self.__location

    @location.setter
    def location(self, location):
        self.__location = location

    def __str__(self):
        msg = "[" + str(self.position_in_path) + "] <" +\
                str(self.kind) + "> " + \
              " S:" + str(self.start_range) + " E:" + \
              str(self.end_range) + " loc: " + str(self.location) + ' ' + \
              self.msg
        return msg
