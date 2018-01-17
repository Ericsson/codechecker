// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

include "shared.thrift"

namespace py Authentication_v6
namespace js codeCheckerAuthentication_v6

struct HandshakeInformation {
  1: bool requiresAuthentication,       // True if the server has a privileged zone.
  2: bool sessionStillActive            // Whether the session in which the HandshakeInformation is returned is a live one
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

  // This method is a dummy stub requiring no permissions. When a server is
  // first accessed, the client should check if the server supports it.
  // This method's call succeeds (and is a no-op), if the server allows the
  // client's API to connect. Otherwise, the RequestFailed exception is thrown.
  void checkAPIVersion()
                       throws (1: shared.RequestFailed requestError),

  // ============= Authentication and session handling =============
  // Get basic authentication information from the server.
  HandshakeInformation getAuthParameters(),


  // Retrieves a list of accepted authentication methods from the server.
  list<string> getAcceptedAuthMethods(),

  // Handles creating a session token for the user.
  string performLogin(1: string authMethod,
                      2: string authString)
                      throws (1: shared.RequestFailed requestError),

  // Performs logout action for the user. Must be called from the
  // corresponding valid session which is to be destroyed.
  bool destroySession()
                      throws (1: shared.RequestFailed requestError),

  // Returns the currently logged in user within the active session, or empty
  // string if no authenticated session is active.
  string getLoggedInUser()
                         throws (1: shared.RequestFailed requestError),


  // ============= Authorization, permission management =============
  // Returns the list of permissions.
  // scope acts as a filter for which scope's permissions to list. Refer to
  // the documentation in api/shared.thrift for the list of valid scopes.
  list<shared.Permission> getPermissions(1: string scope),


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
  list<shared.Permission> getPermissionsForUser(
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
    1: shared.Permission permission,
    2: string            extraParams)
    throws (1: shared.RequestFailed requestError),

  // PERMISSION: Have at least one of the managers of permission argument.
  bool addPermission(1: shared.Permission permission,
                     2: string            authName,
                     3: bool              isGroup,
                     4: string            extraParams)
                     throws (1: shared.RequestFailed requestError),

  // PERMISSION: Have at least one of the managers of permission argument.
  bool removePermission(1: shared.Permission permission,
                        2: string            authName,
                        3: bool              isGroup,
                        4: string            extraParams)
                        throws (1: shared.RequestFailed requestError),

  // Returns whether or not the CURRENTLY LOGGED IN USER is authorised with
  // the given permission. Works even if authentication is disabled on the
  // server, based on the permission's default values. This API call honours
  // permission inheritance.
  bool hasPermission(1: shared.Permission permission,
                     2: string            extraParams)
                     throws (1: shared.RequestFailed requestError)

}
