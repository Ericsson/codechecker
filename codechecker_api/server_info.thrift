// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

namespace py codechecker_api.python.ServerInfo_v6
namespace js codeCheckerServerInfo_v6

service serverInfoService {

  // Returns the CodeChecker version that is running on the server.
  string getPackageVersion();
}
