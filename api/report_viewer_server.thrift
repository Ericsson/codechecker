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
const string API_VERSION = '5.1'
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
  5: optional bool            suppressed = false  // if the bug state is suppressed
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
struct BuildActionData {
  1: i64 id,
  2: i64 runId,
  3: string buildCmd,
  4: string analyzerType,
  5: string file,
  6: string checkCmd,
  7: string failure,
  8: string date,
  9: i64 duration
}
typedef list<BuildActionData> BuildActionDataList

//-----------------------------------------------------------------------------
service codeCheckerDBAccess {

  // get the run Ids and dates from the database to select one run
  RunDataList getRunData()
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

  // get file informations if fileContent is true the content of the source file
  // will be also returned
  SourceFileData getSourceFileData(
                                   1: i64 fileId,
                                   2: bool fileContent)
                                   throws (1: shared.RequestFailed requestError),

  // get the file id from the database for a filepath, returns -1 if not found
  i64 getFileId(1: i64 runId,
                2: string path)
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

  // gives back the build Actions that generate the given report.
  // multiple build actions can belong to a report in a header.
  BuildActionDataList getBuildActions(1: i64 reportId)
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
                                             throws (1: shared.RequestFailed requestError)

}
