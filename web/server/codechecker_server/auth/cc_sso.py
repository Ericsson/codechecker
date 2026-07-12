# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""SSO authentication via OAuth2 authorization code flow."""

import base64
import json
import re
from typing import Any, Dict

import requests

from codechecker_common.logger import get_logger

LOG = get_logger('server')


class AuthError(PermissionError):

    # http error code
    code = 401
    # auth error violation code
    # 100 for unknown authentication error
    # 101-109 sign up errors
    auth_code = 100

    def __init__(self, *args: Any, auth_code: int = 100) -> None:
        super().__init__(*args)
        self.auth_code = auth_code


class DUOAuthError(AuthError):

    def __init__(self, *args: Any) -> None:
        super().__init__(*args, auth_code=104)


def get_base64_encoded_str(string: str) -> str:
    string_bytes = string.encode("ascii")
    base64_bytes = base64.b64encode(string_bytes)
    base64_string = base64_bytes.decode("ascii")
    return base64_string


def _request_auth(data: dict, config: Dict[str, Any]) -> Dict[str, Any]:
    auth_string = f'{config.get("client_id")}:{config.get("client_secret")}'
    header = {
        "Authorization": "Basic " + get_base64_encoded_str(auth_string),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    url = data.pop("url", None)
    payload = "&".join([f"{key}={value}" for key, value in data.items()])
    response = requests.request(method="POST", url=url, headers=header, data=data)
    if response is not None and response.status_code < 300:
        try:
            response = json.loads(s=response.text)
            return response
        except Exception:
            LOG.error("Auth malformed response for {}".format(data))
    else:
        if response.status_code == 302 or response.status_code == 307:
            redirect_url = response.headers["Location"]
            LOG.info("Redirect Url Location Header: {}".format(redirect_url))
            try:
                response = requests.request(
                    method="POST", url=redirect_url, headers=header, data=payload)
                response = json.loads(s=response.text)
                return response
            except Exception:
                LOG.exception(
                    "Auth REDIRECT failed {} for {}".format(
                        response.status_code, data))
        if response is not None:
            LOG.error("Auth failed {} for {}".format(response.status_code, data))
            LOG.error(response.text)
    LOG.error("Failed request to Auth Server")


def get_user_info(access_token: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch SSO user info.

    This API relies on the access_token from the previous steps. The token
    must have the scope "openid profile email", otherwise it will fail.
    """
    if not access_token:
        LOG.error("No valid access token")
        raise DUOAuthError("No valid access token")
    response = requests.get(
        f'{config.get("sso_server")}/userinfo',
        headers={"Authorization": f"Bearer {access_token}"},
    )

    if response is not None and response.status_code < 300:
        try:
            response = json.loads(s=response.text)
            LOG.info("get_user_info - Response: %s",
                     json.dumps(response, indent=4))
            return response
        except Exception:
            LOG.error("Malformed response from SSO when getting user info.")
            raise DUOAuthError(
                "Malformed response from SSO when getting user info.")
    else:
        if response is not None:
            LOG.error(
                "OAuth service error {} for getting user info".format(
                    response.status_code))
            raise DUOAuthError(
                f"OAuth service error {response.status_code} "
                f"for getting user info")
        else:
            LOG.error("Unknown DUO Auth service error")
            raise DUOAuthError("Unknown DUO Auth service error")


def _parse_sso_groups(raw_groups) -> list:
    groups_name = []
    for group in raw_groups:
        if isinstance(group, str):
            match = re.search(r"CN=([^,]+)", group)
            if match:
                groups_name.append(match.group(1))
            else:
                groups_name.append(group)
        else:
            LOG.warning("Unexpected group entry in SSO user info: %s", group)
    return groups_name


def process_user_info(user_info: dict, config: Dict[str, Any]):
    raw_groups = user_info.pop("group", user_info.pop("groups", []))
    user_info["groups"] = _parse_sso_groups(raw_groups)
    return user_info


def validate_token(token: str, config: Dict[str, Any]) -> Dict[str, Any]:
    data = {}
    data["token_hint"] = "access_token"
    data["token"] = token
    data["url"] = f'{config.get("sso_server")}/token_introspection'
    res = _request_auth(data, config)
    LOG.info("validate_token - Response: %s", json.dumps(res, indent=4))
    return process_user_info(get_user_info(token, config), config)


def auth_user(code: str, config: Dict[str, Any]) -> Dict[str, Any]:
    data = {
        "code": code
    }

    data["grant_type"] = "authorization_code"
    data["scope"] = "openid profile email"
    data["redirect_uri"] = config.get("redirect_uri")
    data["url"] = f'{config.get("sso_server")}/token'
    res = _request_auth(data, config)
    access_token = res["access_token"]
    return validate_token(access_token, config)
