# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import sys
import math
import ntpath
import linecache

from abc import ABCMeta

from codechecker_lib import logger
from codechecker_lib import plist_parser

from codechecker_lib.analyzers import result_handler_base

LOG = logger.get_new_logger('RESULT HANDLER DB')

class ResultHandlerPrintOut(result_handler_base.ResultHandler):
    """

    """

    __metaclass__ = ABCMeta
    # handle the output stdout, or plist or both for an analyzer

    def __init__(self, buildaction, workspace):
        super(ResultHandlerPrintOut, self).__init__(buildaction, workspace)
        self.__workspace = workspace
        self.__action_id = None
        self.__print_steps = False

    @property
    def print_steps(self):
        return self.__print_steps

    @print_steps.setter
    def print_steps(self, value):
        self.__print_steps = value

    def __format_location(self, event):
        pos = event.start_pos
        line = linecache.getline(pos.file_path, pos.line)
        if line == '':
            return line

        marker_line = line[0:(pos.col-1)]
        marker_line = ' '  * (len(marker_line) + marker_line.count('\t'))
        return '%s%s^' % (line.replace('\t', '  '), marker_line)

    def __format_bug_event(self, event):
        pos = event.start_pos
        fname = os.path.basename(pos.file_path)
        return '%s:%d:%d: %s' % (fname, pos.line, pos.col, event.msg)

    def postprocess_result(self):
        """
        no postprocessing required
        """
        pass

    def handle_results(self):

        # checked source file set by the analyzer

        LOG.debug('Handling quick check results')
        source = self.analyzed_source_file
        head, source_file_name = ntpath.split(source)
        plist = self.get_analyzer_result_file()

        output = sys.stdout

        if not os.path.isfile(plist):
            LOG.info('Checking %s failed!' % (source_file_name))
            return 1

        try:
            _, bugs = plist_parser.parse_plist(plist)
        except Exception as ex:
            LOG.error('The generated plist is not valid!')
            LOG.error(ex)
            return 1

        err_code = self.analyzer_returncode

        if len(bugs) > 0:
            output.write('%d defect(s) found while checking %s:\n\n' %
                         (len(bugs), source_file_name))
        else:
            output.write('No defects found in %s :-)\n' % source_file_name)
            return err_code

        index_format = '    %%%dd, ' % int(math.floor(math.log10(len(bugs)))+1)

        for bug in bugs:
            last_event = bug.get_last_event()
            output.write(self.__format_bug_event(last_event))
            output.write('\n')
            output.write(self.__format_location(last_event))
            output.write('\n')
            if self.__print_steps:
                output.write('  Steps:\n')
                for index, event in enumerate(bug.events()):
                    output.write(index_format % (index + 1))
                    output.write(self.__format_bug_event(event))
                    output.write('\n')
            output.write('\n')
