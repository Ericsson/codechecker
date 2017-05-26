# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from abc import ABCMeta
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
            events = [i for i in report.bug_path if i.get('kind') == 'event']

            # Skip list handler can be None if no config file is set.
            if self.skiplist_handler:
                # Skip is checked based on the file path of the last reported
                # event.
                # TODO: this should be changed in later versions
                # to use the main diag section to check if the report
                # should be skipped or not.
                f_path = files[events[-1]['location']['file']]
                if events and self.skiplist_handler.should_skip(f_path):
                    LOG.debug(report + ' is skipped (in ' + f_path + ")")
                    continue

            # Create remaining data for bugs and send them to the server.
            bug_paths = []
            report_path = [i for i in report.bug_path if
                           i.get('kind') == 'control']
            for path in report_path:
                try:
                    start_range = path['edges'][0]['start']
                    start_line = start_range[1]['line']
                    start_col = start_range[1]['col']

                    end_range = path['edges'][0]['end']
                    end_line = end_range[1]['line']
                    end_col = end_range[1]['col']
                    source_file_path = files[end_range[1]['file']]
                    bug_paths.append(
                        shared.ttypes.BugPathPos(start_line,
                                                 start_col,
                                                 end_line,
                                                 end_col,
                                                 file_ids[source_file_path]))
                except IndexError:
                    # Edges might be empty nothing can be stored.
                    continue

            bug_events = []
            for event in events:
                file_path = files[event['location']['file']]
                bug_events.append(shared.ttypes.BugPathEvent(
                    event['location']['line'],
                    event['location']['col'],
                    event['location']['line'],
                    event['location']['col'],
                    event['message'],
                    file_ids[file_path]))

            bug_hash = report.main['issue_hash_content_of_line_in_context']
            checker_name = report.main['check_name']
            severity_name = self.severity_map.get(checker_name, 'UNSPECIFIED')
            severity = shared.ttypes.Severity._NAMES_TO_VALUES[severity_name]

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
            supp = sp_handler.get_suppressed()
            if supp:
                connection.add_suppress_bug(self.__run_id, [supp])

            LOG.debug('Storing check results to the database.')

            fpath = files[report.main['location']['file']]
            msg = report.main['description']
            checker_name = report.main['check_name']
            category = report.main['category']
            type = report.main['type']
            report_id = connection.add_report(analisys_id,
                                              file_ids[fpath],
                                              bug_hash,
                                              msg,
                                              bug_paths,
                                              bug_events,
                                              checker_name,
                                              category,
                                              type,
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

            _, source_file_name = os.path.split(self.analyzed_source_file)

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
