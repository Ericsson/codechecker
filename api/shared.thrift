// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

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

struct BugPathPos {
  1: i64    startLine,
  2: i64    startCol,
  3: i64    endLine,
  4: i64    endCol,
  5: i64    fileId
  6: string filePath
}
typedef list<BugPathPos> BugPath

// TODO: This seems to be unused?
struct SuppressBugData {
  1: string bugHash,
  2: string fileName,
  3: string comment
}
typedef list<SuppressBugData> SuppressBugList

struct ConfigValue {
  1: string checkerName,
  2: string attribute,
  3: string value
}
typedef list<ConfigValue> CheckerConfigList

enum Severity{
  UNSPECIFIED   = 0,
  STYLE         = 10,
  LOW           = 20,
  MEDIUM        = 30,
  HIGH          = 40,
  CRITICAL      = 50
}

enum ErrorCode{
  DATABASE,
  IOERROR,
  GENERAL,
  AUTH_DENIED,  // Authentication denied. We do not allow access to the service.
  UNAUTHORIZED, // Authorization denied. User does not have right to perform an action.
  API_MISMATCH  // The client attempted to query an API version that is not supported by the server.
}

exception RequestFailed {
  1: ErrorCode errorCode,
  2: string    message
}

enum ReviewStatus {
  UNREVIEWED,     // Nobody has seen this bug.
  CONFIRMED,      // This is really bug.
  FALSE_POSITIVE, // This is not a bug.
  WONT_FIX        // This is a bug but we don't want to fix it.
}

// DetectionStatus is set by the storage process. When a new bug appears then
// the status is NEW. If the bug disappears during an update process in a run
// then it becomes RESOLVED. If a bug remains in an update process then it
// becomes UNRESOLVED. If a bug was RESOLVED and appears again then it becomes
// REOPENED until it disappears again.
enum DetectionStatus {
  NEW,
  RESOLVED,
  UNRESOLVED,
  REOPENED
}

/**
 * The following permission scopes exist.
 *
 * SYSTEM: These permissions are global to the running CodeChecker server.
 *   In this case, the 'extraParams' field is empty.
 *
 * PRODUCT: These permissions are configured per-product.
 *   The extra data field looks like the following object:
 *     { i64 productID }
*/
enum Permission {
  SUPERUSER        = 1,         // scope: SYSTEM

  PRODUCT_ADMIN    = 16,        // scope: PRODUCT
  PRODUCT_ACCESS   = 17,        // scope: PRODUCT
  PRODUCT_STORE    = 18         // scope: PRODUCT
}
