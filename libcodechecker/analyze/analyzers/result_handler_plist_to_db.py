# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from abc import ABCMeta
import base64
import codecs
from hashlib import sha256
import os

import shared
from codeCheckerDBAccess.ttypes import Encoding

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

    def __store_bugs(self, files, reports, client):
        file_ids = {}
        # Send content of file to the server if needed.
        for file_name in files:
            # Sometimes the file doesn't exist, e.g. when the input of the
            # analysis is pure plist files.
            if not os.path.isfile(file_name):
                LOG.debug(file_name + ' not found, and will not be stored.')
                continue

            with codecs.open(file_name, 'r', 'UTF-8') as source_file:
                file_content = source_file.read()
                # WARN the right content encoding is needed for thrift!
                # TODO: we may not use the file content in the end
                # depending on skippaths.
                source = codecs.encode(file_content, 'utf-8')

            hasher = sha256()
            hasher.update(source)
            content_hash = hasher.hexdigest()
            file_descriptor = client.needFileContent(file_name, content_hash)
            file_ids[file_name] = file_descriptor.fileId

            if file_descriptor.needed:
                source64 = base64.b64encode(source)
                res = client.addFileContent(content_hash,
                                            source64,
                                            Encoding.BASE64)
                if not res:
                    LOG.debug("Failed to store file content")

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
            # In plist file the source and target of the arrows are provided as
            # starting and ending ranges of the arrow. The path A->B->C is
            # given as A->B and B->C, thus range B is provided twice. So in the
            # loop only target points of the arrows are stored, and an extra
            # insertion is done for the source of the first arrow before the
            # loop.
            bug_paths = []
            report_path = [i for i in report.bug_path if
                           i.get('kind') == 'control']

            if report_path:
                try:
                    start_range = report_path[0]['edges'][0]['start']
                    start1_line = start_range[0]['line']
                    start1_col = start_range[0]['col']
                    start2_line = start_range[1]['line']
                    start2_col = start_range[1]['col']
                    source_file_path = files[start_range[1]['file']]
                    bug_paths.append(
                        shared.ttypes.BugPathPos(start1_line,
                                                 start1_col,
                                                 start2_line,
                                                 start2_col,
                                                 file_ids[source_file_path]))
                except IndexError:
                    pass

            for path in report_path:
                try:
                    end_range = path['edges'][0]['end']
                    end1_line = end_range[0]['line']
                    end1_col = end_range[0]['col']
                    end2_line = end_range[1]['line']
                    end2_col = end_range[1]['col']
                    source_file_path = files[end_range[1]['file']]
                    bug_paths.append(
                        shared.ttypes.BugPathPos(end1_line,
                                                 end1_col,
                                                 end2_line,
                                                 end2_col,
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
                bhash, fname, comment = supp
                suppress_data = shared.ttypes.SuppressBugData(bhash,
                                                              fname,
                                                              comment)
                client.addSuppressBug(self.__run_id, [suppress_data])

            LOG.debug('Storing check results to the database.')

            fpath = files[report.main['location']['file']]
            msg = report.main['description']
            checker_name = report.main['check_name']
            category = report.main['category']
            type = report.main['type']

            LOG.debug("Storing report")
            report_id = client.addReport(self.__run_id,
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

            LOG.debug("Storing done for report " + str(report_id))
            report_ids.append(report_id)

    def handle_results(self, client=None):
        """
        Send the plist content to the database.
        Server API calls should be used in one connection.
         - addReport
         - needFileContent
         - addFileContent
        """

        assert self.analyzer_returncode == 0

        plist_file = self.analyzer_result_file

        try:
            files, reports = plist_parser.parse_plist(plist_file)
        except Exception as ex:
            LOG.debug(str(ex))
            msg = 'Parsing the generated result file failed.'
            LOG.error(msg + ' ' + plist_file)
            return 1

        self.__store_bugs(files, reports, client)

    def postprocess_result(self):
        """
        No postprocessing required for plists.
        """
        pass
