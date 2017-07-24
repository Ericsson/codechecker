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
  2: bool sessionStillActive,           // whether the session in which the HandshakeInformation is returned is a valid one
}

service codeCheckerAuthentication {
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
             throws (1: shared.RequestFailed requestError)

}
