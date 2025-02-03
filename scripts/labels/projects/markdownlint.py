# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Markdownlint."""
import json
import os
import re
import subprocess
from typing import Iterable, Tuple

from urllib3.exceptions import HTTPError

from .. import http_ as http


def get_markdownlint_latest_release(request: http.HTMLAcquirer) -> str:
    """Get the version of the latest tag of ``markdownlint``."""
    api = "https://api.github.com/repos/markdownlint/markdownlint/tags"
    response = request.get_url(api)
    if response.status in (http.HTTPStatusCode.UNAUTHORIZED,
                           http.HTTPStatusCode.FORBIDDEN):
        # GitHub API returns "403 Forbidden" for "Rate limit exceeded" cases.
        try:
            github_token = subprocess.check_output(["gh", "auth", "token"]) \
                .decode().strip()
        except Exception:
            try:
                github_token = os.environ["GITHUB_TOKEN"]
            except KeyError:
                # pylint: disable=raise-missing-from
                raise PermissionError("GitHub API rate limit exceeded, "
                                      "specify 'GITHUB_TOKEN' enviromment "
                                      "variable!")

        response = request._pool.request("GET", api, headers={
            "Authorization": f"Bearer {github_token}"
        })

    if response.status != http.HTTPStatusCode.OK:
        raise HTTPError("Failed to get a valid response on second try, got "
                        f"{response.status} {response.reason} instead")

    data = json.loads(response.data)
    return data[0]["name"]


RuleRe = re.compile(r"\s+\* \[(?P<name>MD\d+)[^\]]+\]\(#(?P<anchor>\S+)\)")


def get_markdownlint_rules(request: http.HTMLAcquirer, base_url: str) \
        -> Iterable[Tuple[str, str]]:
    """Returns ``(rule, anchor)`` pairs of ``markdownlint`` rules."""
    raw_data_url = base_url \
        .replace("github.com", "raw.githubusercontent.com", 1) \
        .replace("/blob", '', 1)

    response = request.get_url(raw_data_url)
    for line in response.data.decode().split('\n'):
        match = RuleRe.match(line)
        if not match:
            continue

        yield match.group("name"), match.group("anchor")
