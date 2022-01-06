# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Helper and converter functions for the gerrit review json format."""

import json
import logging
import os
import re

from typing import Dict, List, Union

from codechecker_report_converter.report import Report


LOG = logging.getLogger('report-converter')


def convert(reports: List[Report]) -> Dict:
    """Convert reports to gerrit review format.

    Process the required environment variables and convert the reports
    to the required gerrit json format.
    """
    repo_dir = os.environ.get('CC_REPO_DIR')
    report_url = os.environ.get('CC_REPORT_URL')
    changed_file_path = os.environ.get('CC_CHANGED_FILES')
    changed_files = __get_changed_files(changed_file_path)

    return __convert_reports(reports, repo_dir, report_url,
                             changed_files, changed_file_path)


def mandatory_env_var_is_set():
    """
    True if mandatory environment variables are set otherwise False and print
    error messages.
    """
    no_missing_env_var = True

    if os.environ.get('CC_REPO_DIR') is None:
        LOG.error("When using gerrit output the 'CC_REPO_DIR' environment "
                  "variable needs to be set to the root directory of the "
                  "sources, i.e. the directory where the repository was "
                  "cloned!")
        no_missing_env_var = False

    if os.environ.get('CC_CHANGED_FILES') is None:
        LOG.error("When using gerrit output the 'CC_CHANGED_FILES' "
                  "environment variable needs to be set to the path of "
                  "changed files json from Gerrit!")
        no_missing_env_var = False

    return no_missing_env_var


def __convert_reports(reports: List[Report],
                      repo_dir: Union[str, None],
                      report_url: Union[str, None],
                      changed_files: List[str],
                      changed_file_path: Union[str, None]) -> Dict:
    """Convert the given reports to gerrit json format.

    This function will convert the given report to Gerrit json format.
    reports - list of reports comming from a plist file or
              from the CodeChecker server (both types can be processed)
    repo_dir - Root directory of the sources, i.e. the directory where the
               repository was cloned.
    report_url - URL where the report can be found something like this:
      "http://jenkins_address/userContent/$JOB_NAME/$BUILD_NUM/index.html"
    changed_files - list of the changed files
    checker_labels
    """
    review_comments: Dict[str, List[Dict]] = {}

    report_count = 0
    report_messages_in_unchanged_files = []
    for report in reports:
        file_name = report.file.path

        report_count += 1

        # file_name can be without a path in the report.
        rel_file_path = os.path.relpath(file_name, repo_dir) \
            if repo_dir and os.path.dirname(file_name) != "" else file_name

        checked_file = rel_file_path \
            + ':' + str(report.line) + ":" + str(report.column)

        review_comment_msg = \
            f"[{report.severity}] {checked_file}: {report.message} " \
            f"[{report.checker_name}]\n{report.source_line}"

        # Skip the report if it is not in the changed files.
        if changed_file_path and not \
                any([file_name.endswith(c) for c in changed_files]):
            report_messages_in_unchanged_files.append(review_comment_msg)
            continue

        if rel_file_path not in review_comments:
            review_comments[rel_file_path] = []

        review_comments[rel_file_path].append({
            "range": {
                "start_line": report.line,
                "start_character": report.column,
                "end_line": report.line,
                "end_character": report.column},
            "message": review_comment_msg})

    message = f"CodeChecker found {report_count} issue(s) in the code."

    if report_messages_in_unchanged_files:
        message += ("\n\nThere following reports are introduced in files "
                    "which are not changed and can't be shown as individual "
                    "reports:\n{0}\n".format('\n'.join(
                        report_messages_in_unchanged_files)))

    if report_url:
        message += f" See: {report_url}"

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
    changed_files: List[str] = []

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
