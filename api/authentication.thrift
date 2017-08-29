// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

include "shared.thrift"

namespace py Authentication
namespace js codeCheckerAuthentication

struct HandshakeInformation {
  1: bool requiresAuthentication,       // true if the server has a privileged zone --- the state of having a valid access is not considered here
  2: bool sessionStillActive            // whether the session in which the HandshakeInformation is returned is a valid one
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

struct AuthorisationList {
  1: list<string> users,
  2: list<string> groups
}

// A conjunctive set of filters (a bit mask) that are applied when permissions
// are queried.
struct PermissionFilter {
  1: bool given,      // The user has access the permission.
  2: bool canManage   // The user can manage other users' authorisation to this permission.
}

service codeCheckerAuthentication {
  // ============= Authentication and session handling =============
  // get basic authentication information from the server
  HandshakeInformation getAuthParameters(),

  // retrieves a list of accepted authentication methods from the server
  list<string> getAcceptedAuthMethods(),

  // handles creating a session token for the user
  string performLogin(1: string auth_method,
                      2: string auth_string)
                      throws (1: shared.RequestFailed requestError),

  // performs logout action for the user (must be called from the corresponding valid session)
  bool destroySession()
                      throws (1: shared.RequestFailed requestError),

  // returns currently logged in user within the active session
  // returns empty string if the session is not active
  string getLoggedInUser()
                         throws (1: shared.RequestFailed requestError),


  // ============= Authorization, permission management =============
  // Returns the list of permissions.
  // scope acts as a filter for which scope's permissions to list. Refer to
  // the documentation in api/shared.thrift for the list of valid scopes.
  list<Permission> getPermissions(1: string scope),


  // ----------------------------------------------------------------
  // Refer to the documentation in api/shared.thrift on what data the
  // 'extraParams' field for a particular permission requires.
  // In each case, it has to be a JSON representation of a dict.
  // ----------------------------------------------------------------

  // Get the list of permissions from the CURRENTLY LOGGED IN USER's perspective
  // in the given scope and scope parameters, and filter it based on certain
  // criteria.
  // If no criteria are given, this behaves identically to
  // getPermissions(scope).
  list<Permission> getPermissionsForUser(
    1: string           scope,
    2: string           extraParams,
    3: PermissionFilter filter)
    throws (1: shared.RequestFailed requestError),

  // Returns the list of users and groups with the given permission.
  //
  // This call does NOT honour permission inheritance and only return users
  // and groups whom are DIRECTLY granted the permission.
  //
  // This call is only applicable, if the CURRENTLY LOGGED IN USER has access
  // to manage the given permission.
  AuthorisationList getAuthorisedNames(
    1: Permission permission,
    2: string     extraParams)
    throws (1: shared.RequestFailed requestError),

  // PERMISSION: Have at least one of the managers of permission argument.
  bool addPermission(1: Permission permission,
                     2: string     authName,
                     3: bool       isGroup,
                     4: string     extraParams)
                     throws (1: shared.RequestFailed requestError),

  // PERMISSION: Have at least one of the managers of permission argument.
  bool removePermission(1: Permission permission,
                        2: string     authName,
                        3: bool       isGroup,
                        4: string     extraParams)
                        throws (1: shared.RequestFailed requestError),

  // Returns whether or not the CURRENTLY LOGGED IN USER is authorised with
  // the given permission. Works even if authentication is disabled on the
  // server, based on the permission's default values. This API call honours
  // permission inheritance.
  bool hasPermission(1: Permission permission,
                     2: string     extraParams)
                     throws (1: shared.RequestFailed requestError)

}
