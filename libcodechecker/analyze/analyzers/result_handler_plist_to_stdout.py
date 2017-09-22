# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from abc import ABCMeta
import linecache
import math
import os
import sys

from libcodechecker import suppress_handler
from libcodechecker.analyze import plist_parser
from libcodechecker.analyze.analyzers.result_handler_base import ResultHandler
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('PLIST TO STDOUT')


class PlistToStdout(ResultHandler):
    """
    Result handler for processing a plist file with the
    analysis results and print them to the standard output.
    """

    __metaclass__ = ABCMeta

    def __init__(self, buildaction, workspace, lock):
        super(PlistToStdout, self).__init__(buildaction, workspace)
        self.__print_steps = False
        self.__output = sys.stdout
        self.__lock = lock
        self.suppress_handler = None

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

    @staticmethod
    def __format_location(event, source_file):
        loc = event['location']
        line = linecache.getline(source_file, loc['line'])
        if line == '':
            return line

        marker_line = line[0:(loc['col'] - 1)]
        marker_line = ' ' * (len(marker_line) + marker_line.count('\t'))
        return '%s%s^' % (line.replace('\t', '  '), marker_line)

    @staticmethod
    def __format_bug_event(name, severity, event, source_file):

        loc = event['location']
        fname = os.path.basename(source_file)
        if name:
            return '[%s] %s:%d:%d: %s [%s]' % (severity,
                                               fname,
                                               loc['line'],
                                               loc['col'],
                                               event['message'],
                                               name)
        else:
            return '%s:%d:%d: %s' % (fname,
                                     loc['line'],
                                     loc['col'],
                                     event['message'])

    def __print_bugs(self, reports, files):

        report_num = len(reports)
        if report_num > 0:
            index_format = '    %%%dd, ' % \
                int(math.floor(math.log10(report_num)) + 1)

        non_suppressed = 0
        for report in reports:
            events = [i for i in report.bug_path if i.get('kind') == 'event']
            f_path = files[events[-1]['location']['file']]
            if self.skiplist_handler and \
                    self.skiplist_handler.should_skip(f_path):
                LOG.debug(report + ' is skipped (in ' + f_path + ")")
                continue

            bug = {'hash_value':
                   report.main['issue_hash_content_of_line_in_context'],
                   'file_path': f_path
                   }
            if self.suppress_handler and \
                    self.suppress_handler.get_suppressed(bug):
                LOG.debug("Suppressed by suppress file: {0}".format(report))
                continue

            last_report_event = report.bug_path[-1]
            source_file = files[last_report_event['location']['file']]
            report_line = last_report_event['location']['line']
            report_hash = report.main['issue_hash_content_of_line_in_context']
            checker_name = report.main['check_name']
            sp_handler = suppress_handler.SourceSuppressHandler(source_file,
                                                                report_line,
                                                                report_hash,
                                                                checker_name)

            # Check for suppress comment.
            suppress_data = sp_handler.get_suppressed()
            if suppress_data:
                if self.suppress_handler:
                    LOG.info("Writing source-code suppress at '{0}:{1}' to "
                             "suppress file".format(source_file, report_line))
                    hash_value, file_name, comment = suppress_data
                    self.suppress_handler.store_suppress_bug_id(hash_value,
                                                                file_name,
                                                                comment)

                continue

            severity = self.severity_map.get(checker_name,
                                             'UNSPECIFIED')

            self.__output.write(self.__format_bug_event(checker_name,
                                                        severity,
                                                        last_report_event,
                                                        source_file))
            self.__output.write('\n')
            self.__output.write(self.__format_location(last_report_event,
                                                       source_file))
            self.__output.write('\n')
            if self.__print_steps:
                self.__output.write('  Steps:\n')
                for index, event in enumerate(events):
                    self.__output.write(index_format % (index + 1))
                    source_file = files[event['location']['file']]
                    self.__output.write(self.__format_bug_event(None,
                                                                None,
                                                                event,
                                                                source_file))
                    self.__output.write('\n')
            self.__output.write('\n')

            non_suppressed += 1

        basefile_print = (' ' +
                          os.path.basename(self.analyzed_source_file)) \
            if self.analyzed_source_file and \
            len(self.analyzed_source_file) > 0 else ''

        if non_suppressed == 0:
            self.__output.write('Found no defects while analyzing%s\n' %
                                (basefile_print))
        else:
            self.__output.write(
                'Found %d defect(s) while analyzing%s\n\n' %
                (non_suppressed, basefile_print))

    def handle_results(self, client=None):
        plist = self.analyzer_result_file

        try:
            files, reports = plist_parser.parse_plist(plist)
        except Exception as ex:
            LOG.error('The generated plist is not valid!')
            LOG.error(ex)
            return 1

        err_code = self.analyzer_returncode

        if err_code == 0:
            try:
                # No lock when consuming plist.
                self.__lock.acquire() if self.__lock else None
                self.__print_bugs(reports, files)
            finally:
                self.__lock.release() if self.__lock else None
        else:
            self.__output.write('Analyzing %s with %s failed.\n' %
                                (os.path.basename(self.analyzed_source_file),
                                 self.buildaction.analyzer_type))
        return err_code

    def postprocess_result(self):
        """
        No postprocessing required for plists.
        """
        pass
