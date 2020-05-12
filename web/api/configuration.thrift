// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

include "codechecker_api_shared.thrift"

namespace py Configuration_v6
namespace js codeCheckerConfiguration_v6

service configurationService {

    // Returns Global notification as a base64 encoded string.
    string getNotificationBannerText()

    // The notification text is sent as a base64 encoded string.
    // Call with an empty string to hide the notification banner.
    // PERMISSION: SUPERUSER
    void setNotificationBannerText(1: string notification_b64)
                         throws (1: codechecker_api_shared.RequestFailed requestError)
}
