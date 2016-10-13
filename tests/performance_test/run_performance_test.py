# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import datetime
import os
import zlib
from uuid import uuid4

import test_utils
from shared.ttypes import BugPathEvent
from shared.ttypes import BugPathPos
from test_utils.thrift_client_to_db import CCReportHelper, CCViewerHelper

test_utils.setCCEnv()

# --- constants -------------------------------------------------------------
runNumber = 10
fileSize = 100  # lines
fileNumber = 10
bugPerFile = 10
bugLength = 5
fileContent = zlib.compress('\n'.join(['A' * 80] * fileSize),
                            zlib.Z_BEST_COMPRESSION)


# ---------------------------------------------------------------------------

# -------------------------------------------------------------------------------
def parseArgs():
    import argparse
    global args

    parser = argparse.ArgumentParser(
        description='FixMe')

    parser.add_argument('--output', '-o', dest='output',
                        default=os.path.join(os.path.dirname(__file__),
                                             'results.csv'),
                        help='The path of the output file. Will be overwritten if alredy exists.')

    parser.add_argument('--address', '-a', default='localhost', dest='address',
                        help='The address of the codechecker server.')

    parser.add_argument('--check-port', required=True, type=int,
                        dest='check_port',
                        help='Check port.')

    parser.add_argument('--view-port', required=True, type=int,
                        dest='view_port',
                        help='View port.')

    args = parser.parse_args()


# -------------------------------------------------------------------------------
def main():
    # handle argument parsing
    parseArgs()

    # --- main part -------------------------------------------------------------
    reportTimeList = []
    getTimeList = []

    with CCReportHelper(args.address, args.check_port) as ccReporter, \
            CCViewerHelper(args.address, args.view_port, '/') as ccViewer, \
            open(args.output, 'r+') as outFile:

        outFile.truncate()
        for runCount in range(runNumber):
            before = datetime.datetime.now()
            run_id = ccReporter.addCheckerRun('command', 'name_' + str(
                runCount) + '_' + str(uuid4()),
                                              'version', False)
            report_ids = []
            for fileCount in range(fileNumber):
                print('\nrun: ' + str(runCount + 1) + '/' + str(
                    runNumber) + '\nfile: ' + str(fileCount + 1) + '/' + str(
                    fileNumber))

                file_id = ccReporter.needFileContent(run_id, 'file_' + str(
                    fileCount)).fileId
                ccReporter.addFileContent(file_id, fileContent)

                build_action_id = ccReporter.addBuildAction(run_id,
                                                            'build_cmd_' + str(
                                                                fileCount),
                                                            'check_cmd_' + str(
                                                                fileCount),
                                                            'target_' + str(
                                                                fileCount))

                ccReporter.finishBuildAction(build_action_id, '')
                for bugCount in range(bugPerFile):
                    bug_pathes = []
                    bug_events = []
                    for bugElementCount in range(bugLength):
                        line = bugCount * bugLength + bugElementCount + 1
                        bug_pathes.append(
                            BugPathPos(line, 1, line, 10, file_id))
                        bug_events.append(
                            BugPathEvent(line, 1, line, 10, 'event_msg',
                                         file_id))

                    report_id = ccReporter.addReport(build_action_id,
                                                     file_id,
                                                     'hash_' + str(
                                                         run_id) + '_' + str(
                                                         fileCount) + '_' + str(
                                                         bugCount),
                                                     1,
                                                     'checker_message',
                                                     bug_pathes,
                                                     bug_events,
                                                     'checker_name',
                                                     'checker_cat',
                                                     'bug_type',
                                                     1)
                    report_ids.append(report_id)

            # ccReporter.moduleToReport(run_id, 'module_id', report_ids)
            ccReporter.finishCheckerRun(run_id)

            after = datetime.datetime.now()

            time = (after - before).total_seconds()
            reportTimeList.append(time)

            before = datetime.datetime.now()
            runIDs = [rundata.runId for rundata in ccViewer.getRunData()]
            after = datetime.datetime.now()
            time = (after - before).total_seconds()
            getTimeList.append(time)

            before = datetime.datetime.now()
            res = ccViewer.getAllRunResults(runIDs[-1])
            after = datetime.datetime.now()
            time = (after - before).total_seconds()
            getTimeList.append(time)

            before = datetime.datetime.now()
            ccViewer.getReportDetails(res[-1].reportId)
            after = datetime.datetime.now()
            time = (after - before).total_seconds()
            getTimeList.append(time)

            s = str(runCount) + ';' + str(reportTimeList[-1]) + ';' + str(
                getTimeList[-3]) + ';' + str(getTimeList[-2]) + ';' + str(
                getTimeList[-1])
            print(s)
            outFile.write(s + '\n')


# -------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
