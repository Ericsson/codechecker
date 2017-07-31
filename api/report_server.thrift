// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

// =================================================
//  !!! Update version information if api changes!!!
// =================================================
//  backward incompatible changes should increase major version
//  other changes should only increase minor version

include "shared.thrift"

namespace py codeCheckerDBAccess
namespace js codeCheckerDBAccess
namespace cpp cc.service.codechecker

//=================================================
const string API_VERSION = '6.0'
const i64 MAX_QUERY_SIZE = 500
//=================================================

//-----------------------------------------------------------------------------
struct RunData{
  1: i64            runId,        // unique id of the run
  2: string         runDate,      // date of the run
  3: string         name,         // human readable name of the run
  4: i64            duration,     // duration of the run; -1 if not finished
  5: i64            resultCount,  // number of results in the run
  6: string         runCmd,       // the used check command
  7: optional bool  can_delete    // true if codeCheckerDBAccess::removeRunResults()
                                  // is allowed on this run (see issue 151)
}
typedef list<RunData> RunDataList

//-----------------------------------------------------------------------------
struct ReportData{
  1: string              checkerId,       // the qualified id of the checker that reported this
  2: string              bugHash,         // This is unique id of the concrete report.
  3: string              checkedFile,     // this is a filepath
  4: string              checkerMsg,      // description of the bug report
  5: i64                 reportId,        // id of the report in the current run in the db
  6: bool                suppressed,      // true if the bug is suppressed
  7: i64                 fileId,          // unique id of the file the report refers to
  8: shared.BugPathEvent lastBugPosition  // This contains the range and message of the last item in the symbolic
                                          // execution step list.
  9: shared.Severity     severity         // checker severity
  10: optional string    suppressComment  // suppress commment if report is suppressed
}
typedef list<ReportData> ReportDataList

//-----------------------------------------------------------------------------
/**
 * Members of this struct are interpreted in "AND" relation with each other.
 * So they need to match a single report at the same time.
 */
struct ReportFilter{
  1: optional string          filepath,           // In the filters a single wildcard can be be used: *
  2: optional string          checkerMsg,
  3: optional shared.Severity severity,
  4: optional string          checkerId,          // should filter in the fully qualified checker id name such as alpha.core.
                                                  // the analyzed system. Projects can optionally use this concept.
  5: optional bool            suppressed = false, // if the bug state is suppressed
  6: optional string          bugHash
}

/**
 * If there is a list of ReportFilter, there is an OR relation between the list members.
 */
typedef list<ReportFilter> ReportFilterList

//-----------------------------------------------------------------------------
struct ReportDetails{
  1: shared.BugPathEvents pathEvents,
  2: shared.BugPath       executionPath
}

//-----------------------------------------------------------------------------
// TODO: This type is unused.
struct ReportFileData{
  1: i64    reportFileId,
  2: string reportFileContent
}

//-----------------------------------------------------------------------------
// default sorting of the results
enum SortType {
  FILENAME,
  CHECKER_NAME,
  SEVERITY
}

//-----------------------------------------------------------------------------
enum Encoding {
  DEFAULT,
  BASE64
}

//-----------------------------------------------------------------------------
struct SourceFileData{
  1: i64             fileId,
  2: string          filePath,
  3: optional string fileContent
}

//-----------------------------------------------------------------------------
enum Order {
  ASC,
  DESC
}

//-----------------------------------------------------------------------------
struct SortMode{
  1: SortType type,
  2: Order    ord
}

//-----------------------------------------------------------------------------
struct ReportDataTypeCount{
  1: string          checkerId,
  2: shared.Severity severity,
  3: i64             count
}
typedef list<ReportDataTypeCount> ReportDataTypeCountList

//-----------------------------------------------------------------------------
struct SkipPathData{
  1: string  path,
  2: string  comment
}
typedef list<SkipPathData> SkipPathDataList

//-----------------------------------------------------------------------------
// diff result types
enum DiffType {
  NEW,
  RESOLVED,
  UNRESOLVED
}

//-----------------------------------------------------------------------------
struct NeedFileResult {
                1: bool needed;
                2: i64 fileId;
}

//-----------------------------------------------------------------------------
struct CommentData {
  1: i64 id,
  2: string author,
  3: string message,
  4: string createdAt
}
typedef list<CommentData> CommentDataList

//-----------------------------------------------------------------------------
service codeCheckerDBAccess {

  // get the run Ids and dates from the database to select one run
  RunDataList getRunData(1: string runNameFilter)
                         throws (1: shared.RequestFailed requestError),

  ReportData getReport(
                       1: i64 reportId)
                       throws (1: shared.RequestFailed requestError),

  // get the results for one runId
  ReportDataList getRunResults(
                               1: i64 runId,
                               2: i64 limit,
                               3: i64 offset,
                               4: list<SortMode> sortType,
                               5: ReportFilterList reportFilters)
                               throws (1: shared.RequestFailed requestError),

  // count all the results for one run
  i64 getRunResultCount(
                        1: i64 runId,
                        2: ReportFilterList reportFilters)
                        throws (1: shared.RequestFailed requestError),

  // gives back the all marked region and message for a report
  ReportDetails getReportDetails(
                                 1: i64 reportId)
                                 throws (1: shared.RequestFailed requestError),

  // get file information, if fileContent is true the content of the source
  // file will be also returned
  SourceFileData getSourceFileData(
                                   1: i64 fileId,
                                   2: bool fileContent,
                                   3: Encoding encoding)
                                   throws (1: shared.RequestFailed requestError),

  // suppress the bug
  bool suppressBug(1: list<i64> runIds,
                   2: i64 reportId,
                   3: string comment)
                   throws (1: shared.RequestFailed requestError),

  // unsuppress the bug
  bool unSuppressBug(1: list<i64> runIds,
                     2: i64 reportId)
                     throws (1: shared.RequestFailed requestError),

  // get suppressed bugs in a run
  shared.SuppressBugList getSuppressedBugs(1: i64 run_id)
                                          throws(1: shared.RequestFailed requestError),

  // get comments for a bug
  CommentDataList getComments(1: i64 reportId)
                              throws(1: shared.RequestFailed requestError),

  // count all the comments for one bug
  i64 getCommentCount(1: i64 reportId)
                      throws(1: shared.RequestFailed requestError),

  // add new comment for a bug
  bool addComment(1: i64 reportId,
                  2: CommentData comment)
                  throws(1: shared.RequestFailed requestError),

  // update a comment
  bool updateComment(1: i64 commentId,
                     2: string newMessage)
                     throws(1: shared.RequestFailed requestError),

  // remove a comment
  bool removeComment(1: i64 commentId)
                     throws(1: shared.RequestFailed requestError),

  // get the md documentation for a checker
  string getCheckerDoc(1: string checkerId)
                       throws (1: shared.RequestFailed requestError),

  // compare the results of two runs
  ReportDataList getNewResults(1: i64 base_run_id,
                               2: i64 new_run_id,
                               3: i64 limit,
                               4: i64 offset,
                               5: list<SortMode> sortType,
                               6: ReportFilterList reportFilters )
                               throws (1: shared.RequestFailed requestError),

  ReportDataList getResolvedResults(1: i64 base_run_id,
                                    2: i64 new_run_id,
                                    3: i64 limit,
                                    4: i64 offset,
                                    5: list<SortMode> sortType,
                                    6: ReportFilterList reportFilters )
                                    throws (1: shared.RequestFailed requestError),

  ReportDataList getUnresolvedResults(1: i64 base_run_id,
                                      2: i64 new_run_id,
                                      3: i64 limit,
                                      4: i64 offset,
                                      5: list<SortMode> sortType,
                                      6: ReportFilterList reportFilters )
                                      throws (1: shared.RequestFailed requestError),

  // get the checker configuration values
  shared.CheckerConfigList getCheckerConfigs(1: i64 runId)
                                             throws (1: shared.RequestFailed requestError),

  // get the skip list of paths
  SkipPathDataList getSkipPaths(1: i64 runId)
                                throws (1: shared.RequestFailed requestError),

  // get all the results for one runId
  // count all results for a checker
  ReportDataTypeCountList getRunResultTypes(1: i64 runId,
                                            2: ReportFilterList reportFilters)
                                            throws (1: shared.RequestFailed requestError),

  // returns the database access handler api version
  string getAPIVersion();

  // returns the CodeChecker version that is running on the server
  string getPackageVersion();

  // remove bug results from the database
  bool removeRunResults(1: list<i64> runIds)
                        throws (1: shared.RequestFailed requestError),

  // get the suppress file path set by the command line
  // returns empty string if not set
  string getSuppressFile()
                        throws (1: shared.RequestFailed requestError),

  // count the diff results
  i64 getDiffResultCount(1: i64 base_run_id,
                         2: i64 new_run_id,
                         3: DiffType diff_type,
                         4: ReportFilterList reportFilters)
                         throws (1: shared.RequestFailed requestError),

  // count all the diff results for each checker
  ReportDataTypeCountList getDiffResultTypes(1: i64 base_run_id,
                                             2: i64 new_run_id,
                                             3: DiffType diff_type,
                                             4: ReportFilterList reportFilters)
                                             throws (1: shared.RequestFailed requestError),


  //============================================
  // Analysis result storage related API calls.
  //============================================

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
                      2: shared.SuppressBugList bugsToSuppress
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
  i64  addReport(
                 1: i64 run_id,
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


  // * If (filepath, content_hash) is in the DB return (existing fileId, false).
  // * If only the content_hash matches, a (new fileId, false) is returned.
  // * If the filepath matches, but content_hash not, a (new file_id, true) is returned.
  // * If none of them matches a (new file_id, true) is returned.
  NeedFileResult needFileContent(
                                 1: string filepath,
                                 2: string content_hash)
                                 throws (1: shared.RequestFailed requestError),

  bool addFileContent(
                      1: string content_hash,
                      2: string file_content,
                      3: Encoding encoding)
                      throws (1: shared.RequestFailed requestError),

  bool finishCheckerRun(1: i64 run_id)
                        throws (1: shared.RequestFailed requestError),

  bool setRunDuration(1: i64 run_id,
                      2: i64 duration)
                      throws (1: shared.RequestFailed requestError),

  bool stopServer()
                  throws (1: shared.RequestFailed requestError)

}
