# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
result handlers for the clang static analyzer
"""

import os
import sys
import math
import ntpath
import linecache

from codechecker_lib import client
from codechecker_lib import logger
from codechecker_lib import plist_parser

from codechecker_lib import suppress_handler
import shared

from codechecker_lib.analyzers import result_handler_base

LOG = logger.get_new_logger('CLANG_SA_RESULT_HANDLER')


class DBResHandler(result_handler_base.ResultHandler):
    """
    stores the results to a database
    """

    def __init__(self, buildaction, workspace, run_id):
        super(DBResHandler, self).__init__(buildaction, workspace)
        self.__workspace = workspace
        self.__run_id = run_id

    def postprocess_result(self):
        """
        no postprocessing required for clang static analyzer
        """
        pass

    def handle_results(self):
        """
        send the plist content to the database
        server API calls should be used in one connection
         - addBuildAction
         - addReport
         - needFileContent
         - addFileContent
         - finishBuildAction
        """

        with client.get_connection() as connection:

            LOG.debug('Handling results for clangSA, storing to the database')

            LOG.debug('Storing original build and analyzer command to the database')
            analisys_id = connection.add_build_action(self.__run_id,
                                                      self.buildaction.original_command,
                                                      ' '.join(self.analyzer_cmd))

            # store buildaction and analyzer command to the database

            _, source_file_name = ntpath.split(self.analyzed_source_file)

            if self.analyzer_returncode == 0:

                LOG.info('Analysing ' + source_file_name +
                         ' with ClangSA was successful.')

                plist_file = self.get_analyzer_result_file()

                try:
                    files, bugs = plist_parser.parse_plist(plist_file)
                except Exception as ex:
                    LOG.debug(str(ex))
                    msg = 'Parsing the generated result file failed'
                    LOG.error(msg + ' ' + plist_file)
                    connection.finish_build_action(analisys_id, msg)
                    return 1

                file_ids = {}
                # Send content of file to the server if needed
                for file_name in files:
                    file_descriptor = connection.need_file_content(self.__run_id,
                                                                   file_name)
                    file_ids[file_name] = file_descriptor.fileId
                    if file_descriptor.needed:
                        with open(file_name, 'r') as source_file:
                            file_content = source_file.read()
                        import zlib
                        compressed_file = zlib.compress(file_content, zlib.Z_BEST_COMPRESSION)
                        # TODO: we may not use the file content in the end
                        # depending on skippaths
                        LOG.debug('storing file content to the database')
                        connection.add_file_content(file_descriptor.fileId,
                                                           compressed_file)

                # skipping bugs in header files handled here
                report_ids = []
                for bug in bugs:
                    events = bug.events()

                    # skip list handler can be None if no config file is set
                    if self.skiplist_handler:
                        if events and self.skiplist_handler.should_skip(events[-1].start_pos.file_path):
                            # Issue #20: this bug is in a file which should be skipped
                            LOG.debug(bug.hash_value + ' is skipped (in ' +
                                      events[-1].start_pos.file_path + ")")
                            continue

                    # create remaining data for bugs and send them to the server
                    bug_paths = []
                    for path in bug.paths():
                        bug_paths.append(
                            shared.ttypes.BugPathPos(path.start_pos.line,
                                                     path.start_pos.col,
                                                     path.end_pos.line,
                                                     path.end_pos.col,
                                                     file_ids[path.start_pos.file_path]))

                    bug_events = []
                    for event in bug.events():
                        bug_events.append(shared.ttypes.BugPathEvent(event.start_pos.line,
                            event.start_pos.col, event.end_pos.line, event.end_pos.col,
                            event.msg, file_ids[event.start_pos.file_path]))

                    bug_hash = bug.hash_value

                    severity_name = self.severity_map.get(bug.checker_name, 'UNSPECIFIED')
                    severity = shared.ttypes.Severity._NAMES_TO_VALUES[severity_name]

                    suppress = False

                    source_file = bug.file_path
                    last_bug_event = bug.events()[-1]
                    bug_line = last_bug_event.start_pos.line

                    sp_handler = suppress_handler.SourceSuppressHandler(source_file,
                                                                        bug_line)
                    # check for suppress comment
                    supp = sp_handler.check_source_suppress()
                    if supp:
                        # something shoud be suppressed
                        suppress_checkers = sp_handler.suppressed_checkers()

                        if bug.checker_name in suppress_checkers or \
                           suppress_checkers == ['all']:
                            suppress = True

                            file_path, file_name = ntpath.split(source_file)

                            # checker_hash, file_name, comment
                            to_suppress = (bug_hash,
                                           file_name,
                                           sp_handler.suppress_comment())

                            LOG.debug(to_suppress)

                            connection.add_suppress_bug(self.__run_id, [to_suppress])

                    LOG.debug('Storing check results to the database')

                    report_id = connection.add_report(analisys_id,
                                                      file_ids[bug.file_path],
                                                      bug_hash,
                                                      bug.msg,
                                                      bug_paths,
                                                      bug_events,
                                                      bug.checker_name,
                                                      bug.category,
                                                      bug.type,
                                                      severity,
                                                      suppress)

                    report_ids.append(report_id)
            else:
                LOG.info('Analysing ' + source_file_name +
                         ' with clangSA failed.')

            connection.finish_build_action(analisys_id, self.analyzer_stderr)


class QCResHandler(result_handler_base.ResultHandler):
    """
    prints the results to the standard output
    """
    def __init__(self, buildaction, workspace):
        super(QCResHandler, self).__init__(buildaction, workspace)
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
