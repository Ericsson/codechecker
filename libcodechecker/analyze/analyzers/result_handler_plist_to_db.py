# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from abc import ABCMeta
import ntpath
import os
import zlib

import shared

from libcodechecker import client
from libcodechecker import logger
from libcodechecker import suppress_handler
from libcodechecker.analyze import plist_parser
from libcodechecker.analyze.analyzers.result_handler_base import ResultHandler
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('PLIST TO DB')


class PlistToDB(ResultHandler):
    """
    Result handler for processing a plist file with the
    analysis results and stores them to the database.
    """

    __metaclass__ = ABCMeta

    def __init__(self, buildaction, workspace, run_id):
        super(PlistToDB, self).__init__(buildaction, workspace)
        self.__run_id = run_id

    def __store_bugs(self, files, reports, connection, analisys_id):
        file_ids = {}
        # Send content of file to the server if needed.
        for file_name in files:
            file_descriptor = connection.need_file_content(self.__run_id,
                                                           file_name)
            file_ids[file_name] = file_descriptor.fileId

            # Sometimes the file doesn't exist, e.g. when the input of the
            # analysis is pure plist files.
            if not os.path.isfile(file_name):
                LOG.debug(file_name + ' not found, and will not be stored.')
                continue

            if file_descriptor.needed:
                with open(file_name, 'r') as source_file:
                    file_content = source_file.read()
                compressed_file = zlib.compress(file_content,
                                                zlib.Z_BEST_COMPRESSION)
                # TODO: we may not use the file content in the end
                # depending on skippaths.
                LOG.debug('storing file content to the database')
                connection.add_file_content(file_descriptor.fileId,
                                            compressed_file)

        # Skipping reports in header files handled here.
        report_ids = []
        for report in reports:
            events = report.events()

            # Skip list handler can be None if no config file is set.
            if self.skiplist_handler:
                # Skip is checked based on the file path of the last reported
                # event.
                # TODO: this should be changed in later versions
                # to use the main diag section to check if the report
                # should be skipped or not.
                if events and self.skiplist_handler.should_skip(
                        events[-1].location.file_path):
                    LOG.debug(report.hash_value + ' is skipped (in ' +
                              events[-1].location.file_path + ")")
                    continue

            # Create remaining data for bugs and send them to the server.
            bug_paths = []
            for path in report.paths():
                source_file_path = path.start_range.end.file_path
                bug_paths.append(
                    shared.ttypes.BugPathPos(path.start_range.begin.line,
                                             path.start_range.begin.col,
                                             path.end_range.end.line,
                                             path.end_range.end.col,
                                             file_ids[source_file_path]))

            bug_events = []
            for event in report.events():
                bug_events.append(shared.ttypes.BugPathEvent(
                    event.location.line,
                    event.location.col,
                    event.location.line,
                    event.location.col,
                    event.msg,
                    file_ids[event.location.file_path]))

            bug_hash = report.hash_value

            severity_name = self.severity_map.get(report.checker_name,
                                                  'UNSPECIFIED')
            severity = shared.ttypes.Severity._NAMES_TO_VALUES[severity_name]

            sp_handler = suppress_handler.SourceSuppressHandler(report)

            # Check for suppress comment.
            supp = sp_handler.get_suppressed()
            if supp:
                connection.add_suppress_bug(self.__run_id, [supp])

            LOG.debug('Storing check results to the database.')

            fpath = report.obsolate_main_section.location.file_path
            report_id = connection.add_report(analisys_id,
                                              file_ids[fpath],
                                              bug_hash,
                                              report.obsolate_main_section.msg,
                                              bug_paths,
                                              bug_events,
                                              report.checker_name,
                                              report.category,
                                              report.type,
                                              severity,
                                              supp is not None)

            report_ids.append(report_id)

    def handle_results(self):
        """
        Send the plist content to the database.
        Server API calls should be used in one connection.
         - addBuildAction
         - addReport
         - needFileContent
         - addFileContent
         - finishBuildAction
        """

        with client.get_connection() as connection:

            LOG.debug('Storing original build and analyzer command '
                      'to the database.')

            _, source_file_name = ntpath.split(self.analyzed_source_file)

            if LoggerFactory.get_log_level() == logger.DEBUG:
                analyzer_cmd = ' '.join(self.analyzer_cmd)
            else:
                analyzer_cmd = ''

            build_cmd_hash = self.buildaction.original_command_hash
            analysis_id = \
                connection.add_build_action(self.__run_id,
                                            build_cmd_hash,
                                            analyzer_cmd,
                                            self.buildaction.analyzer_type,
                                            source_file_name)

            assert self.analyzer_returncode == 0

            plist_file = self.analyzer_result_file

            try:
                files, reports = plist_parser.parse_plist(plist_file)
            except Exception as ex:
                LOG.debug(str(ex))
                msg = 'Parsing the generated result file failed.'
                LOG.error(msg + ' ' + plist_file)
                connection.finish_build_action(analysis_id, msg)
                return 1

            self.__store_bugs(files, reports, connection, analysis_id)

            connection.finish_build_action(analysis_id, self.analyzer_stderr)

    def postprocess_result(self):
        """
        No postprocessing required for plists.
        """
        pass
