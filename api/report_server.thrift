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
  8: map<shared.DetectionStatus, i32> detectionStatusCount
                                  // this maps the detection status to its count
}
typedef list<RunData> RunDataList

struct ReviewData{
  1: shared.ReviewStatus  status,
  2: string               comment,
  3: string               author,
  4: string               date
}

//-----------------------------------------------------------------------------
struct ReportData{
  1: string              checkerId,       // the qualified id of the checker that reported this
  2: string              bugHash,         // This is unique id of the concrete report.
  3: string              checkedFile,     // this is a filepath
  4: string              checkerMsg,      // description of the bug report
  5: i64                 reportId,        // id of the report in the current run in the db
  6: i64                 fileId,          // unique id of the file the report refers to
  7: shared.BugPathEvent lastBugPosition  // This contains the range and message of the last item in the symbolic
                                          // execution step list.
  8: shared.Severity     severity         // checker severity
  9: ReviewData          review           // bug review status informations.
  10: shared.DetectionStatus detectionStatus  // state of the bug (see the enum constant values)
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
  5: optional string          bugHash
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
  SEVERITY,
  REVIEW_STATUS,
  DETECTION_STATUS
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

  // change review status of a bug.
  bool changeReviewStatus(1: i64 reportId,
                          2: shared.ReviewStatus status,
                          3: string message)
                          throws (1: shared.RequestFailed requestError),

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

  // The client can ask the server whether a file is already stored in the
  // database. If it is, then it is not necessary to send it in the ZIP file
  // with massStoreRun() function. This function requires a list of file hashes
  // (sha256) and returns the ones which are not stored yet.
  list<string> necessaryFileContents(
                                     1: list<string> file_hashes)
                                     throws (1: shared.RequestFailed requestError),

  // This function stores an entire run encapsulated and sent in a ZIP file.
  // The ZIP file has to be compressed and sent as a base64 encoded string. The
  // ZIP file must contain exactly one directory which has a "reports" and an
  // optional "root" sub-folder. The former one is the output of "CodeChecker
  // analyze" command and the latter one contains the source files on absolute
  // paths starting as if "root" was the "/" directory. The source files are
  // not necessary to be wrapped in the ZIP file (see necessaryFileContents()
  // function).
  // The "version" parameter is the used CodeChecker version which checked this
  // run.
  // The "force" parameter removes existing analysis results for a run.
  i64 massStoreRun(
                   1: string run_name,
                   2: string version,
                   3: string zipfile,
                   4: bool force)
                   throws (1: shared.RequestFailed requestError),

  bool replaceConfigInfo(
                     1: i64 run_id,
                     2: shared.CheckerConfigList values)
                     throws (1: shared.RequestFailed requestError),

}
