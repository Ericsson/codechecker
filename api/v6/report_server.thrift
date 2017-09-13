// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

include "shared.thrift"

namespace py codeCheckerDBAccess_v6
namespace js codeCheckerDBAccess_v6

//=================================================
const i64 MAX_QUERY_SIZE = 500
//=================================================

struct RunData {
  1: i64            runId,        // Unique id of the run.
  2: string         runDate,      // Date of the run last updated.
  3: string         name,         // Human-given identifier.
  4: i64            duration,     // Duration of the run (-1 if not finished).
  5: i64            resultCount,  // Number of results in the run.
  6: string         runCmd,       // The used check command.
  // This maps the detection status to its count
  7: map<shared.DetectionStatus, i32> detectionStatusCount
}
typedef list<RunData> RunDataList

/**
 * Members of this struct are interpreted in "AND" relation with each other.
 */
struct RunFilter {
  1: list<i64> runIds,
  2: string    name
}

struct RunReportCount {
  1: i64            runId,        // unique id of the run
  2: string         name,         // human readable name of the run
  3: i64            reportCount
}
typedef list<RunReportCount> RunReportCounts

struct CheckerCount {
  1: string             name,     // Name of the checker.
  2: shared.Severity    severity, // Severity level of the checker.
  3: i64                count     // Number of reports.
}
typedef list<CheckerCount> CheckerCounts

struct ReviewData {
  1: shared.ReviewStatus  status,
  2: string               comment,
  3: string               author,
  4: string               date
}

struct ReportData {
  1: i64                     runId,           // Unique id of the run.
  2: string                  checkerId,       // The qualified name of the checker that reported this.
  3: string                  bugHash,         // This is unique id of the concrete report.
  4: string                  checkedFile,     // This is a filepath, the original main file the analyzer was called with.
  5: string                  checkerMsg,      // Description of the bug report.
  6: i64                     reportId,        // id of the report in the current run in the db.
  7: i64                     fileId,          // Unique id of the file the report refers to.
  8: i64                     line,            // line number or the reports main section (not part of the path).
  9: i64                     column,          // column number of the report main section (not part of the path).
  10: shared.Severity        severity         // Checker severity.
  11: ReviewData             reviewData       // Bug review status information.
  12: shared.DetectionStatus detectionStatus  // State of the bug (see the enum constant values).
}
typedef list<ReportData> ReportDataList

/**
 * Members of this struct are interpreted in "OR" relation with each other.
 * Between the members there is "AND" relation.
 */
struct ReportFilter {
  1: list<string>                 filepath,
  2: list<string>                 checkerMsg,
  3: list<string>                 checkerName,
  4: list<string>                 reportHash,
  5: list<shared.Severity>        severity,
  6: list<shared.ReviewStatus>    reviewStatus,
  7: list<shared.DetectionStatus> detectionStatus
}

struct ReportDetails{
  1: shared.BugPathEvents pathEvents,
  2: shared.BugPath       executionPath
}

// TODO: This type is unused.
struct ReportFileData {
  1: i64    reportFileId,
  2: string reportFileContent
}

// default sorting of the results
enum SortType {
  FILENAME,
  CHECKER_NAME,
  SEVERITY,
  REVIEW_STATUS,
  DETECTION_STATUS
}

enum Encoding {
  DEFAULT,
  BASE64
}

struct SourceFileData {
  1: i64             fileId,
  2: string          filePath,
  3: optional string fileContent
}

enum Order {
  ASC,
  DESC
}

struct SortMode {
  1: SortType type,
  2: Order    ord
}

struct ReportDataTypeCount {
  1: string          checkerId,
  2: shared.Severity severity,
  3: i64             count
}
typedef list<ReportDataTypeCount> ReportDataTypeCountList

struct SkipPathData {
  1: string  path,
  2: string  comment
}
typedef list<SkipPathData> SkipPathDataList

// diff result types
enum DiffType {
  NEW,
  RESOLVED,
  UNRESOLVED
}

struct CommentData {
  1: i64    id,
  2: string author,
  3: string message,
  4: string createdAt
}
typedef list<CommentData> CommentDataList


// CompareData is used as an optinal argument for multiple API calls.
// If not set the API calls will just simply filter or query the
// database for results or metrics.
// If set the API calls can be used in a compare mode where
// the results or metrics will be compared to the values set in the CompareData.
// In compare mode the baseline run ids should be set on the API
// (to what the results/metrics will be copared to) and the new run ids and the
// diff type should be set in the CompareData type.
struct CompareData {
  1: list<i64> runIds,
  2: DiffType  diffType
}

service codeCheckerDBAccess {

  // Gives back all analyzed runs.
  // PERMISSION: PRODUCT_ACCESS
  RunDataList getRunData(1: RunFilter runFilter)
                         throws (1: shared.RequestFailed requestError),

  // PERMISSION: PRODUCT_ACCESS
  ReportData getReport(
                       1: i64 reportId)
                       throws (1: shared.RequestFailed requestError),

  // Get the results for some runIds
  // can be used in diff mode if cmpData is set.
  // PERMISSION: PRODUCT_ACCESS
  ReportDataList getRunResults(
                               1: list<i64> runIds,
                               2: i64 limit,
                               3: i64 offset,
                               4: list<SortMode> sortType,
                               5: ReportFilter reportFilter,
                               6: CompareData cmpData)
                               throws (1: shared.RequestFailed requestError),


  // Count the results separately for multiple runs.
  // If an empty run id list is provided the report
  // counts will be calculated for all of the available runs.
  // PERMISSION: PRODUCT_ACCESS
  RunReportCounts getRunReportCounts(
                                   1: list<i64> runIds,
                                   2: ReportFilter reportFilter)
                                   throws (1: shared.RequestFailed requestError),

  // Count all the results some runIds can be used for diff counting.
  // PERMISSION: PRODUCT_ACCESS
  i64 getRunResultCount(
                        1: list<i64> runIds,
                        2: ReportFilter reportFilter,
                        3: CompareData cmpData)
                        throws (1: shared.RequestFailed requestError),

  // gives back the all marked region and message for a report
  // PERMISSION: PRODUCT_ACCESS
  ReportDetails getReportDetails(
                                 1: i64 reportId)
                                 throws (1: shared.RequestFailed requestError),

  // get file information, if fileContent is true the content of the source
  // file will be also returned
  // PERMISSION: PRODUCT_ACCESS
  SourceFileData getSourceFileData(
                                   1: i64 fileId,
                                   2: bool fileContent,
                                   3: Encoding encoding)
                                   throws (1: shared.RequestFailed requestError),

  // change review status of a bug.
  // PERMISSION: PRODUCT_ACCESS or PRODUCT_STORE
  bool changeReviewStatus(1: i64 reportId,
                          2: shared.ReviewStatus status,
                          3: string message)
                          throws (1: shared.RequestFailed requestError),

  // get comments for a bug
  // PERMISSION: PRODUCT_ACCESS
  CommentDataList getComments(1: i64 reportId)
                              throws(1: shared.RequestFailed requestError),

  // count all the comments for one bug
  // PERMISSION: PRODUCT_ACCESS
  i64 getCommentCount(1: i64 reportId)
                      throws(1: shared.RequestFailed requestError),

  // add new comment for a bug
  // PERMISSION: PRODUCT_ACCESS
  bool addComment(1: i64 reportId,
                  2: CommentData comment)
                  throws(1: shared.RequestFailed requestError),

  // update a comment
  // PERMISSION: PRODUCT_ACCESS
  bool updateComment(1: i64 commentId,
                     2: string newMessage)
                     throws(1: shared.RequestFailed requestError),

  // remove a comment
  // PERMISSION: PRODUCT_ACCESS
  bool removeComment(1: i64 commentId)
                     throws(1: shared.RequestFailed requestError),

  // get the md documentation for a checker
  string getCheckerDoc(1: string checkerId)
                       throws (1: shared.RequestFailed requestError),

  // get the checker configuration values
  // PERMISSION: PRODUCT_ACCESS or PRODUCT_STORE
  shared.CheckerConfigList getCheckerConfigs(1: i64 runId)
                                             throws (1: shared.RequestFailed requestError),

  // get the skip list of paths
  // PERMISSION: PRODUCT_ACCESS
  SkipPathDataList getSkipPaths(1: i64 runId)
                                throws (1: shared.RequestFailed requestError),

  // returns the CodeChecker version that is running on the server
  string getPackageVersion();

  // remove bug results from the database
  // PERMISSION: PRODUCT_STORE
  bool removeRunResults(1: list<i64> runIds)
                        throws (1: shared.RequestFailed requestError),

  // get the suppress file path set by the command line
  // returns empty string if not set
  // PERMISSION: PRODUCT_ACCESS
  string getSuppressFile()
                        throws (1: shared.RequestFailed requestError),


  // If the run id list is empty the metrics will be counted
  // for all of the runs and in compare mode all of the runs
  // will be used as a baseline excluding the runs in compare data.
  // PERMISSION: PRODUCT_ACCESS
  map<shared.Severity, i64> getSeverityCounts(1: list<i64> runIds,
                                              2: ReportFilter reportFilter,
                                              3: CompareData cmpData)
                                              throws (1: shared.RequestFailed requestError),

  // If the run id list is empty the metrics will be counted
  // for all of the runs and in compare mode all of the runs
  // will be used as a baseline excluding the runs in compare data.
  // PERMISSION: PRODUCT_ACCESS
  map<string, i64> getCheckerMsgCounts(1: list<i64> runIds,
                                       2: ReportFilter reportFilter,
                                       3: CompareData cmpData)
                                       throws (1: shared.RequestFailed requestError),

  // If the run id list is empty the metrics will be counted
  // for all of the runs and in compare mode all of the runs
  // will be used as a baseline excluding the runs in compare data.
  // PERMISSION: PRODUCT_ACCESS
  map<shared.ReviewStatus, i64> getReviewStatusCounts(1: list<i64> runIds,
                                                      2: ReportFilter reportFilter,
                                                      3: CompareData cmpData)
                                                      throws (1: shared.RequestFailed requestError),

  // If the run id list is empty the metrics will be counted
  // for all of the runs and in compare mode all of the runs
  // will be used as a baseline excluding the runs in compare data.
  // PERMISSION: PRODUCT_ACCESS
  map<shared.DetectionStatus, i64> getDetectionStatusCounts(1: list<i64> runIds,
                                                            2: ReportFilter reportFilter,
                                                            3: CompareData cmpData)
                                                            throws (1: shared.RequestFailed requestError),

  // If the run id list is empty the metrics will be counted
  // for all of the runs and in compare mode all of the runs
  // will be used as a baseline excluding the runs in compare data.
  // PERMISSION: PRODUCT_ACCESS
  map<string, i64> getFileCounts(1: list<i64> runIds,
                                 2: ReportFilter reportFilter,
                                 3: CompareData cmpData)
                                 throws (1: shared.RequestFailed requestError),

  // If the run id list is empty the metrics will be counted
  // for all of the runs and in compare mode all of the runs
  // will be used as a baseline excluding the runs in compare data.
  // PERMISSION: PRODUCT_ACCESS
  CheckerCounts getCheckerCounts(1: list<i64> runIds,
                                 2: ReportFilter reportFilter,
                                 3: CompareData cmpData)
                                 throws (1: shared.RequestFailed requestError),


  //============================================
  // Analysis result storage related API calls.
  //============================================

  // The client can ask the server whether a file is already stored in the
  // database. If it is, then it is not necessary to send it in the ZIP file
  // with massStoreRun() function. This function requires a list of file hashes
  // (sha256) and returns the ones which are not stored yet.
  // PERMISSION: PRODUCT_STORE
  list<string> getMissingContentHashes(
                                       1: list<string> fileHashes)
                                       throws (1: shared.RequestFailed requestError),

  // This function stores an entire run encapsulated and sent in a ZIP file.
  // The ZIP file has to be compressed and sent as a base64 encoded string. The
  // ZIP file must contain a "reports" and an optional "root" sub-folder.
  // The former one is the output of 'CodeChecker analyze' command and the
  // latter one contains the source files on absolute paths starting as if
  // "root" was the "/" directory. The source files are not necessary to be
  // wrapped in the ZIP file (see getMissingContentHashes() function).
  //
  // The "version" parameter is the used CodeChecker version which checked this
  // run.
  // The "force" parameter removes existing analysis results for a run.
  // PERMISSION: PRODUCT_STORE
  i64 massStoreRun(
                   1: string runName,
                   2: string version,
                   3: string zipfile,
                   4: bool   force)
                   throws (1: shared.RequestFailed requestError),

  // PERMISSION: PRODUCT_STORE
  bool replaceConfigInfo(
                     1: i64 runId,
                     2: shared.CheckerConfigList values)
                     throws (1: shared.RequestFailed requestError),

}
