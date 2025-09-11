# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

OAUTH_TEMPLATES = {
    "default": {
        "callback_url": "{host}/login/OAuthLogin/{provider}",
    },
    "github/v1": {
        "authorization_url": "https://github.com/login/oauth/authorize",
        "callback_url": "{host}/login/OAuthLogin/{provider}",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_info_url": "https://api.github.com/user",
        "user_emails_url": "https://api.github.com/user/emails",
        "scope": "user:email",
        "user_info_mapping": {
            "username": "email"
        }
    },
    "google/v1": {
        "authorization_url": "https://accounts.google.com/o/oauth2/auth",
        "callback_url": "{host}/login/OAuthLogin/{provider}",
        "token_url": "https://accounts.google.com/o/oauth2/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v1/userinfo",
        "scope": "openid email profile",
        "user_info_mapping": {
            "username": "email"
        }
    },
    "ms_entra/v2.0": {
        "authorization_url":
            "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",  # noqa
        "callback_url": "{host}/login/OAuthLogin/{provider}",
        "token_url":
            "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        "user_groups_url":
            "https://graph.microsoft.com/v1.0/me/memberOf",
        "jwks_url":
            "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",  # noqa
        "user_info_url": "https://graph.microsoft.com/v1.0/me",
        "scope": "User.Read email profile openid offline_access",
        "user_info_mapping": {
            "username": "email"
        }
    },
    "gitlab/v1": {
        "authorization_url": "https://gitlab.com/oauth/authorize",
        "callback_url": "{host}/login/OAuthLogin/{provider}",
        "token_url": "https://gitlab.com/oauth/token",
        "user_info_url": "https://gitlab.com/oauth/userinfo",
        "scope": "openid email profile",
        "user_info_mapping": {
            "username": "email"
        }
    }
}
