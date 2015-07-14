// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

//-----------------------------------------------------------------------------
struct BugPathEvent {
  1: i64    startLine,
  2: i64    startCol,
  3: i64    endLine,
  4: i64    endCol,
  5: string msg,
  6: i64    fileId
  7: string filePath
}
typedef list<BugPathEvent> BugPathEvents

//-----------------------------------------------------------------------------
struct BugPathPos {
  1: i64    startLine,
  2: i64    startCol,
  3: i64    endLine,
  4: i64    endCol,
  5: i64    fileId
  6: string filePath
}
typedef list<BugPathPos> BugPath

//-----------------------------------------------------------------------------
struct ConfigValue {
  1: string checker_name,
  2: string attribute,
  3: string value
}
typedef list<ConfigValue> CheckerConfigList

//-----------------------------------------------------------------------------
enum Severity{
  UNSPECIFIED   = 0,
  STYLE         = 10,
  LOW           = 20,
  MEDIUM        = 30,
  HIGH          = 40,
  CRITICAL      = 50
}

//-----------------------------------------------------------------------------
enum ErrorCode{
  DATABASE,
  IOERROR
}

//-----------------------------------------------------------------------------
exception RequestFailed {
  1: ErrorCode error_code,
  2: string    message
}

