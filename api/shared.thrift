// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

enum ErrorCode {
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
