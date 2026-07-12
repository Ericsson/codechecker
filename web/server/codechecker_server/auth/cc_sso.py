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
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from codechecker_common.logger import get_logger

LOG = get_logger('server')

SSO_SCOPE = "openid profile email"


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


class SSOAuthError(AuthError):

    def __init__(self, *args: Any) -> None:
        super().__init__(*args, auth_code=104)


def get_base64_encoded_str(string: str) -> str:
    string_bytes = string.encode("ascii")
    base64_bytes = base64.b64encode(string_bytes)
    base64_string = base64_bytes.decode("ascii")
    return base64_string


def _request_auth(data: dict, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    url = data.pop("url", None)
    if not url:
        LOG.error("Auth request URL is missing")
        return None

    auth_string = f'{config.get("client_id")}:{config.get("client_secret")}'
    header = {
        "Authorization": "Basic " + get_base64_encoded_str(auth_string),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    form_data = urlencode(data)

    try:
        response = requests.post(
            url=url, headers=header, data=form_data, timeout=30)
    except requests.RequestException as exc:
        LOG.error("Auth request failed for %s: %s", url, exc)
        return None

    if response is not None and response.status_code < 300:
        try:
            return json.loads(s=response.text)
        except json.JSONDecodeError:
            LOG.error("Auth malformed response for %s", url)
            return None

    if response is not None:
        if response.status_code in (302, 307):
            redirect_url = response.headers.get("Location")
            if redirect_url:
                LOG.info("Redirect Url Location Header: %s", redirect_url)
                try:
                    redirect_response = requests.post(
                        url=redirect_url, headers=header, data=form_data,
                        timeout=30)
                    if redirect_response.status_code < 300:
                        return json.loads(s=redirect_response.text)
                except (requests.RequestException, json.JSONDecodeError):
                    LOG.exception(
                        "Auth redirect failed for %s", redirect_url)

        LOG.error("Auth failed %s for %s", response.status_code, url)
        LOG.error(response.text)

    LOG.error("Failed request to Auth Server")
    return None


def get_user_info(access_token: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch SSO user info.

    This API relies on the access_token from the previous steps. The token
    must have the scope "openid profile email", otherwise it will fail.
    """
    if not access_token:
        LOG.error("No valid access token")
        raise SSOAuthError("No valid access token")

    sso_server = config.get("sso_server")
    if not sso_server:
        raise SSOAuthError("SSO server URL is not configured")

    try:
        response = requests.get(
            f'{sso_server}/userinfo',
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30)
    except requests.RequestException as exc:
        LOG.error("SSO userinfo request failed: %s", exc)
        raise SSOAuthError("SSO userinfo request failed") from exc

    if response is not None and response.status_code < 300:
        try:
            user_info = json.loads(s=response.text)
            LOG.info("get_user_info - Response: %s",
                     json.dumps(user_info, indent=4))
            return user_info
        except json.JSONDecodeError as exc:
            LOG.error("Malformed response from SSO when getting user info.")
            raise SSOAuthError(
                "Malformed response from SSO when getting user info.") from exc

    if response is not None:
        LOG.error(
            "OAuth service error %s for getting user info",
            response.status_code)
        raise SSOAuthError(
            f"OAuth service error {response.status_code} "
            f"for getting user info")

    LOG.error("Unknown SSO Auth service error")
    raise SSOAuthError("Unknown SSO Auth service error")


def _parse_sso_groups(raw_groups) -> list:
    groups_name = []
    if not raw_groups:
        return groups_name

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


def _resolve_username(user_info: dict, config: Dict[str, Any]) -> str:
    username_claim = config.get("username_claim")
    if username_claim:
        username = user_info.get(username_claim)
        if username:
            return str(username)

    for claim in ("preferred_username", "email", "sub"):
        username = user_info.get(claim)
        if username:
            return str(username)

    return ""


def process_user_info(user_info: dict, config: Dict[str, Any]):
    raw_groups = user_info.pop("group", user_info.pop("groups", []))
    user_info["groups"] = _parse_sso_groups(raw_groups)
    user_info["username"] = _resolve_username(user_info, config)
    return user_info


def validate_token(token: str, config: Dict[str, Any]) -> Dict[str, Any]:
    user_info = get_user_info(token, config)
    return process_user_info(user_info, config)


def auth_user(code: str, config: Dict[str, Any]) -> Dict[str, Any]:
    if not code:
        raise SSOAuthError("Authorization code is missing")

    data = {
        "code": code,
        "grant_type": "authorization_code",
        "scope": SSO_SCOPE,
        "redirect_uri": config.get("redirect_uri"),
        "url": f'{config.get("sso_server")}/token',
    }
    res = _request_auth(data, config)
    if not res or not res.get("access_token"):
        raise SSOAuthError("SSO token exchange failed")

    return validate_token(res["access_token"], config)
