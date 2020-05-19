# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
import os
import json

from ..output_parser import Message, Event, BaseParser

LOG = logging.getLogger('ReportConverter')


class InferMessage(Message):
    """ Represents a message with an optional event, fixit and note messages.

    This will be a diagnostic section in the plist which represents a report.
    """

    def __init__(self, path, line, column, message, checker, report_hash,
                 events=None, notes=None, fixits=None):
        super(InferMessage, self).__init__(path, line, column, message,
                                           checker, events, notes, fixits)
        self.report_hash = report_hash

    def __eq__(self, other):
        return super(InferMessage, self).__eq__(other) and \
            self.report_hash == other.report_hash

    def __str__(self):
        return '%s, report_hash=%s' % \
               (super(InferMessage, self).__str__(), self.report_hash)


class InferParser(BaseParser):
    """ Parser for Infer output. """

    def __init__(self):
        super(InferParser, self).__init__()
        self.infer_out_parent_dir = None

    def parse_messages(self, analyzer_result):
        """ Parse the given analyzer result. """
        if os.path.isdir(analyzer_result):
            report_file = os.path.join(analyzer_result, "report.json")
            self.infer_out_parent_dir = os.path.dirname(analyzer_result)
        else:
            report_file = analyzer_result
            self.infer_out_parent_dir = os.path.dirname(
                os.path.dirname(analyzer_result))

        if not os.path.exists(report_file):
            LOG.error("Report file does not exist: %s", report_file)
            return

        try:
            with open(report_file, 'r',
                      encoding="utf-8", errors="ignore") as report_f:
                reports = json.load(report_f)
        except IOError:
            LOG.error("Failed to parse the given analyzer result '%s'. Please "
                      "give a infer output directory which contains a valid "
                      "'report.json' file.", analyzer_result)
            return

        for report in reports:
            message = self.__parse_report(report)
            if message:
                self.messages.append(message)

        return self.messages

    def __get_abs_path(self, source_path):
        """ Returns full path of the given source path.
        It will try to find the given source path relative to the given
        analyzer report directory (infer-out).
        """
        if os.path.exists(source_path):
            return source_path

        full_path = os.path.join(self.infer_out_parent_dir, source_path)
        if os.path.exists(full_path):
            return full_path

        LOG.warning("No source file found: %s", source_path)

    def __parse_report(self, bug):
        """ Parse the given report and create a message from them. """
        report_hash = bug['hash']
        checker_name = bug['bug_type']

        message = bug['qualifier']
        line = int(bug['line'])
        col = int(bug['column'])
        if col < 0:
            col = 0

        source_path = self.__get_abs_path(bug['file'])
        if not source_path:
            return

        events = []
        for bug_trace in bug['bug_trace']:
            event = self.__parse_bug_trace(bug_trace)

            if event:
                events.append(event)

        return InferMessage(source_path, line, col, message, checker_name,
                            report_hash, events)

    def __parse_bug_trace(self, bug_trace):
        """ Creates event from a bug trace element. """
        source_path = self.__get_abs_path(bug_trace['filename'])
        if not source_path:
            return

        message = bug_trace['description']
        line = int(bug_trace['line_number'])
        col = int(bug_trace['column_number'])
        if col < 0:
            col = 0

        return Event(source_path, line, col, message)
