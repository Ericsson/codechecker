// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

enum ErrorCode {
  DATABASE,
  IOERROR,
  GENERAL,
  AUTH_DENIED,  // Authentication denied. We do not allow access to the service.
  UNAUTHORIZED, // Authorization denied. User does not have right to perform an action.
  API_MISMATCH, // The client attempted to query an API version that is not supported by the server.
  SOURCE_FILE,  // The client sent a source code which contains errors (e.g.: source code comment errors).
}

exception RequestFailed {
  1: ErrorCode    errorCode,
  2: string       message,
  3: list<string> extraInfo
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
  PRODUCT_STORE    = 18,         // scope: PRODUCT
  PRODUCT_VIEW     = 19         // scope: PRODUCT
}

/**
* Status information about the database backend.
*/
enum DBStatus {
  OK,                           // Everything is ok with the database.
  MISSING,                      // The database is missing.
  FAILED_TO_CONNECT,            // Failed to connect to the database.
  SCHEMA_MISMATCH_OK,           // Schema mismatch between the server and the database.
  SCHEMA_MISMATCH_NO,           // No automatic migration is available.
  SCHEMA_MISSING,               // Schema is missing from the database.
  SCHEMA_INIT_ERROR,            // Failed to create initial database schema.
  SCHEMA_UPGRADE_FAILED         // Failed to upgrade schema.
}
