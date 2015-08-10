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


// The order of the functions inditaces the order that must be maintained when
// calling into the server.
service CheckerReport {
                i64  addCheckerRun(
                                   1: string command,
                                   2: string name,
                                   3: string version,
                                   4: bool update)
                                   throws (1: shared.RequestFailed requestError),

                bool addConfigInfo(
                                   1: i64 run_id,
                                   2: shared.CheckerConfigList values)
                                   throws (1: shared.RequestFailed requestError),

                # the map contains a hash and a comment (can be empty)
                bool addSuppressBug(
                                    1: i64 run_id,
                                    2: map<string, string> hashes)
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
                               4: i64 bug_hash_type,
                               5: string checker_message,
                               6: shared.BugPath bugpath,
                               7: shared.BugPathEvents events,
                               8: string checker_id,
                               9: string checker_cat,
                               10: string bug_type,
                               11: shared.Severity severity)
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
