// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

include "shared.thrift"

namespace py DBThriftAPI

struct NeedFileResult {
                1: bool needed;
                2: i64 fileId;
}

struct SuppressBugData {
    1: string bug_hash,
    2: string file_name,
    3: string comment
}
typedef list<SuppressBugData> SuppressBugList

// The order of the functions inditaces the order that must be maintained when
// calling into the server.
service CheckerReport {
                // store checker run related data to the database
                // by default updates the results if name was already found
                // using the force flag removes existing analysis results for a run
                i64  addCheckerRun(
                                   1: string command,
                                   2: string name,
                                   3: string version,
                                   4: bool force)
                                   throws (1: shared.RequestFailed requestError),

                bool replaceConfigInfo(
                                   1: i64 run_id,
                                   2: shared.CheckerConfigList values)
                                   throws (1: shared.RequestFailed requestError),

                bool addSuppressBug(
                                    1: i64 run_id,
                                    2: SuppressBugList bugsToSuppress
                                    )
                                    throws (1: shared.RequestFailed requestError),

                # remove all suppress information from the database
                bool cleanSuppressData(
                                    1: i64 run_id,
                                    )
                                    throws (1: shared.RequestFailed requestError),

                # the map contains a path and a comment (can be empty)
                bool addSkipPath(
                                 1: i64 run_id,
                                 2: map<string, string> paths)
                                 throws (1: shared.RequestFailed requestError),


                // The next few following functions must be called via the same connection.
                // =============================================================
                i64  addBuildAction(
                                    1: i64 run_id,
                                    2: string build_cmd,
                                    3: string check_cmd)
                                    throws (1: shared.RequestFailed requestError),

                i64  addReport(
                               1: i64 build_action_id,
                               2: i64 file_id,
                               3: string bug_hash,
                               4: string checker_message,
                               5: shared.BugPath bugpath,
                               6: shared.BugPathEvents events,
                               7: string checker_id,
                               8: string checker_cat,
                               9: string bug_type,
                               10: shared.Severity severity,
                               11: bool suppress)
                               throws (1: shared.RequestFailed requestError),

                bool finishBuildAction(
                                       1: i64 action_id,
                                       2: string failure)
                                       throws (1: shared.RequestFailed requestError),

                NeedFileResult needFileContent(
                                               1: i64 run_id,
                                               2: string filepath)
                                               throws (1: shared.RequestFailed requestError),

                bool addFileContent(
                                    1: i64 file_id,
                                    2: binary file_content)
                                    throws (1: shared.RequestFailed requestError),

                bool finishCheckerRun(1: i64 run_id)
                                      throws (1: shared.RequestFailed requestError),

                bool stopServer()
                                throws (1: shared.RequestFailed requestError)
}
