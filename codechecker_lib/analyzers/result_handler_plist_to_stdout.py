# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import linecache
import math
import ntpath
import os
import sys
from abc import ABCMeta

from codechecker_lib import logger
from codechecker_lib import plist_parser
from codechecker_lib.analyzers.result_handler_base import ResultHandler

LOG = logger.get_new_logger('PLIST TO STDOUT')


class PlistToStdout(ResultHandler):
    """
    Result handler for processing a plist file with the
    analysis results and print them to the standard output.
    """

    __metaclass__ = ABCMeta

    def __init__(self, buildaction, workspace):
        super(PlistToStdout, self).__init__(buildaction, workspace)
        self.__print_steps = False
        self.__output = sys.stdout

    @property
    def print_steps(self):
        """
        Print the multiple steps for a bug if there is any.
        """
        return self.__print_steps

    @print_steps.setter
    def print_steps(self, value):
        """
        Print the multiple steps for a bug if there is any.
        """
        self.__print_steps = value

    def __format_location(self, event):
        pos = event.start_pos
        line = linecache.getline(pos.file_path, pos.line)
        if line == '':
            return line

        marker_line = line[0:(pos.col - 1)]
        marker_line = ' ' * (len(marker_line) + marker_line.count('\t'))
        return '%s%s^' % (line.replace('\t', '  '), marker_line)

    def __format_bug_event(self, event):
        pos = event.start_pos
        fname = os.path.basename(pos.file_path)
        return '%s:%d:%d: %s' % (fname, pos.line, pos.col, event.msg)

    def __print_bugs(self, bugs):

        index_format = '    %%%dd, ' % int(
            math.floor(math.log10(len(bugs))) + 1)

        for bug in bugs:
            last_event = bug.get_last_event()
            self.__output.write(self.__format_bug_event(last_event))
            self.__output.write('\n')
            self.__output.write(self.__format_location(last_event))
            self.__output.write('\n')
            if self.__print_steps:
                self.__output.write('  Steps:\n')
                for index, event in enumerate(bug.events()):
                    self.__output.write(index_format % (index + 1))
                    self.__output.write(self.__format_bug_event(event))
                    self.__output.write('\n')
            self.__output.write('\n')

    def handle_plist(self, plist):
        try:
            _, bugs = plist_parser.parse_plist(plist)
        except Exception as ex:
            LOG.error('The generated plist is not valid!')
            LOG.error(ex)
            return 1

        if len(bugs) > 0:
            self.__output.write(
                "%s contains %d defect(s)\n\n" % (plist, len(bugs)))
            self.__print_bugs(bugs)
        else:
            self.__output.write("%s doesn't contain any defects\n" % plist)

    def handle_results(self):

        source = self.analyzed_source_file
        _, source_file_name = ntpath.split(source)
        plist = self.get_analyzer_result_file()

        try:
            _, bugs = plist_parser.parse_plist(plist)
        except Exception as ex:
            LOG.error('The generated plist is not valid!')
            LOG.error(ex)
            return 1

        err_code = self.analyzer_returncode

        if err_code == 0:

            if len(bugs) > 0:
                self.__output.write(
                    '%s found %d defect(s) while analyzing %s\n\n' %
                    (self.buildaction.analyzer_type, len(bugs),
                     source_file_name))
                self.__print_bugs(bugs)
            else:
                self.__output.write('%s found no defects while analyzing %s\n' %
                                    (self.buildaction.analyzer_type,
                                     source_file_name))
                return err_code
        else:
            self.__output.write('Analyzing %s with %s failed.\n' %
                                (source_file_name,
                                 self.buildaction.analyzer_type))
            return err_code
