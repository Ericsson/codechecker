# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Helper and converter functions for the gerrit review json format."""

from typing import Dict, List, Union
from codechecker_common.report import Report

import os
import re
import json


def convert(reports: List[Report], severity_map: Dict[str, str]) -> Dict:
    """Convert reports to gerrit review format.

    Process the required environment variables and convert the reports
    to the required gerrit json format.
    """
    repo_dir = os.environ.get('CC_REPO_DIR')
    report_url = os.environ.get('CC_REPORT_URL')
    changed_file_path = os.environ.get('CC_CHANGED_FILES')
    changed_files = __get_changed_files(changed_file_path)

    gerrit_reports = __convert_reports(reports, repo_dir, report_url,
                                       changed_files, changed_file_path,
                                       severity_map)
    return gerrit_reports


def __convert_reports(reports: List[Report],
                      repo_dir: str,
                      report_url: str,
                      changed_files: List[str],
                      changed_file_path: str,
                      severity_map: Dict[str, str]) -> Dict:
    """Convert the given reports to gerrit json format.

    This function will convert the given report to Gerrit json format.
    reports - list of reports comming from a plist file or
              from the CodeChecker server (both types can be processed)
    repo_dir - Root directory of the sources, i.e. the directory where the
               repository was cloned.
    report_url - URL where the report can be found something like this:
      "http://jenkins_address/userContent/$JOB_NAME/$BUILD_NUM/index.html"
    changed_files - list of the changed files
    severity_map
    """
    review_comments = {}

    report_count = 0
    for report in reports:
        bug_line = report.line
        bug_col = report.col

        check_name = report.check_name
        severity = severity_map.get(check_name, "UNSPECIFIED")
        file_name = report.file_path
        checked_file = file_name \
            + ':' + str(bug_line) + ":" + str(bug_col)
        check_msg = report.description
        source_line = report.line
        # Skip the report if it is not in the changed files.
        if changed_file_path and not \
                any([file_name.endswith(c) for c in changed_files]):
            continue

        report_count += 1
        rel_file_path = os.path.relpath(file_name, repo_dir) \
            if repo_dir else file_name

        if rel_file_path not in review_comments:
            review_comments[rel_file_path] = []

        review_comment_msg = "[{0}] {1}: {2} [{3}]\n{4}".format(
            severity, checked_file, check_msg, check_name, source_line)

        review_comments[rel_file_path].append({
            "range": {
                "start_line": bug_line,
                "start_character": bug_col,
                "end_line": bug_line,
                "end_character": bug_col},
            "message": review_comment_msg})

    message = "CodeChecker found {0} issue(s) in the code.".format(
        report_count)

    if report_url:
        message += " See: '{0}'".format(report_url)

    review = {"tag": "jenkins",
              "message": message,
              "labels": {
                  "Code-Review": -1 if report_count else 1,
                  "Verified": -1 if report_count else 1},
              "comments": review_comments}
    return review


def __get_changed_files(changed_file_path: Union[None, str]) -> List[str]:
    """Return a list of changed files.

    Process the given gerrit changed file object and return a list of
    file paths which changed.

    The file can contain some garbage values at start, so we use regex
    to find a json object.
    """
    changed_files = []

    if not changed_file_path or not os.path.exists(changed_file_path):
        return changed_files

    with open(changed_file_path,
              encoding='utf-8',
              errors='ignore') as changed_file:
        content = changed_file.read()

        # The file can contain some garbage values at start, so we use
        # regex search to find a json object.
        match = re.search(r'\{[\s\S]*\}', content)
        if not match:
            return changed_files

        for filename in json.loads(match.group(0)):
            if "/COMMIT_MSG" in filename:
                continue

            changed_files.append(filename)

    return changed_files
