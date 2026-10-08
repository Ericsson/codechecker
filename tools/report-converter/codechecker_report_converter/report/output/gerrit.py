# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Helper and converter functions for the gerrit review json format.

Besides the environment variables which describe where the reports come
from, the review itself can be configured with the following variables:

CC_GERRIT_LABELS
    Comma separated list of the Gerrit labels the review should vote on,
    e.g. 'Code-Review,Verified'. A label can be assigned the vote values
    used when the review fails and when it passes, separated by a slash,
    e.g. 'Verified=-1/1,Code-Review=-1/0'. If the vote values are not
    given then -1 is used on failure and +1 on success. An empty value
    means that the reports are sent as comments without any vote. If this
    variable is not set then the review keeps its legacy behaviour and
    votes on 'Code-Review' and 'Verified' with -1/+1 whenever a report is
    found.

CC_GERRIT_FAIL_ON_SEVERITY
    The lowest severity level which makes the review fail, e.g. 'HIGH'.
    Reports with a lower severity are still sent as comments but they
    don't result in a negative vote. If this variable is not set then any
    report makes the review fail (legacy behaviour).

CC_GERRIT_TAG
    Tag of the Gerrit review. Defaults to 'jenkins'.
"""

import json
import logging
import os
import re

from dataclasses import dataclass
from typing import Any


from codechecker_report_converter.report import Report


LOG = logging.getLogger('report-converter')


# Severity levels ordered from the least to the most severe.
SEVERITY_ORDER = [
    'UNSPECIFIED', 'STYLE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

# Severity values which were already reported as unknown. It is used to
# avoid logging the same warning for every report.
UNKNOWN_SEVERITIES: set[str] = set()


@dataclass
class GerritLabel:
    """A Gerrit label voted by the review and the values voted with it."""

    name: str
    on_failure: int = -1
    on_success: int = 1


@dataclass
class GerritConfig:
    """Configuration of the Gerrit review output."""

    tag: str
    labels: list[GerritLabel]
    # The lowest severity level which makes the review fail. If it is None
    # then any report makes the review fail.
    fail_severity: str | None = None


def convert(reports: list[Report]) -> dict:
    """Convert reports to gerrit review format.

    Process the required environment variables and convert the reports
    to the required gerrit json format.
    """
    repo_dir = os.environ.get('CC_REPO_DIR')
    report_url = os.environ.get('CC_REPORT_URL')
    changed_file_path = os.environ.get('CC_CHANGED_FILES')
    changed_files = __get_changed_files(changed_file_path)

    config = __read_config()

    if os.environ.get('CC_GERRIT_LABELS') is None:
        LOG.warning(
            "The 'CC_GERRIT_LABELS' environment variable is not set, so the "
            "gerrit review uses its legacy behaviour and votes on "
            "'Code-Review' and 'Verified' with -1/+1 whenever a report is "
            "found. Set this variable to choose which labels are voted on "
            "and with what values, e.g. "
            "'CC_GERRIT_LABELS=Verified=-1/1,Code-Review=-1/0', or set it to "
            "an empty value to send the reports without any vote. Use the "
            "'CC_GERRIT_FAIL_ON_SEVERITY' variable to only fail the review "
            "if an issue at or above the given severity level is found.")

    return __convert_reports(reports, repo_dir, report_url,
                             changed_files, changed_file_path,
                             config=config)


def mandatory_env_var_is_set() -> bool:
    """
    True if mandatory environment variables are set and the Gerrit specific
    ones have a valid value, otherwise False and print error messages.
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

    try:
        __read_config()
    except ValueError as err:
        LOG.error("%s", err)
        no_missing_env_var = False

    return no_missing_env_var


def __read_config() -> GerritConfig:
    """Read the configuration of the review from the environment.

    Raise a ValueError if any of the Gerrit specific environment variables
    has an invalid value.
    """
    tag = os.environ.get('CC_GERRIT_TAG') or 'jenkins'

    labels_value = os.environ.get('CC_GERRIT_LABELS')
    labels = __default_labels() if labels_value is None \
        else __parse_labels(labels_value)

    fail_severity = None
    severity = os.environ.get('CC_GERRIT_FAIL_ON_SEVERITY')
    if severity is not None:
        fail_severity = __parse_severity(severity)

    return GerritConfig(tag=tag, labels=labels, fail_severity=fail_severity)


def __default_labels() -> list[GerritLabel]:
    """Labels voted by the review if 'CC_GERRIT_LABELS' is not set."""
    return [GerritLabel('Code-Review'), GerritLabel('Verified')]


def __parse_labels(value: str) -> list[GerritLabel]:
    """Parse the value of the 'CC_GERRIT_LABELS' environment variable."""
    labels: list[GerritLabel] = []

    for entry in value.split(','):
        entry = entry.strip()
        if not entry:
            continue

        name, _, votes = entry.partition('=')
        name = name.strip()
        if not name:
            raise ValueError(
                f"Invalid label '{entry}' in the 'CC_GERRIT_LABELS' "
                "environment variable: the label name is missing. Expected "
                "'<label name>' or '<label name>=<failure value>/<success "
                "value>', e.g. 'Verified=-1/1,Code-Review=-1/0'.")

        on_failure, on_success = -1, 1
        if votes:
            failure_value, separator, success_value = votes.partition('/')
            if not separator:
                raise ValueError(
                    f"Invalid label '{entry}' in the 'CC_GERRIT_LABELS' "
                    "environment variable: the failure and the success vote "
                    "values must be separated by a slash, e.g. "
                    "'Verified=-1/1'.")

            on_failure = __parse_vote(failure_value, entry)
            on_success = __parse_vote(success_value, entry)

        labels.append(GerritLabel(name, on_failure, on_success))

    return labels


def __parse_vote(value: str, entry: str) -> int:
    """Parse a vote value of a label of 'CC_GERRIT_LABELS'."""
    try:
        vote = int(value)
    except ValueError:
        raise ValueError(
            f"Invalid vote value '{value}' in label '{entry}' of the "
            "'CC_GERRIT_LABELS' environment variable: it must be an "
            "integer.") from None

    if not -2 <= vote <= 2:
        raise ValueError(
            f"Invalid vote value '{value}' in label '{entry}' of the "
            "'CC_GERRIT_LABELS' environment variable: it must be between "
            "-2 and 2.")

    return vote


def __parse_severity(value: str) -> str:
    """Parse the value of the 'CC_GERRIT_FAIL_ON_SEVERITY' env variable."""
    severity = value.strip().upper()
    if severity not in SEVERITY_ORDER:
        raise ValueError(
            f"Invalid severity '{value}' in the "
            "'CC_GERRIT_FAIL_ON_SEVERITY' environment variable. It must be "
            f"one of: {', '.join(SEVERITY_ORDER)}.")

    return severity


def __severity_rank(severity: str | None) -> int:
    """Return the position of the given severity in SEVERITY_ORDER.

    Unknown and missing severity values are considered as 'UNSPECIFIED'.
    """
    if severity is None:
        return SEVERITY_ORDER.index('UNSPECIFIED')

    severity = severity.upper()
    if severity not in SEVERITY_ORDER:
        if severity not in UNKNOWN_SEVERITIES:
            UNKNOWN_SEVERITIES.add(severity)
            LOG.warning("Unknown severity '%s' is considered as "
                        "'UNSPECIFIED'.", severity)

        return SEVERITY_ORDER.index('UNSPECIFIED')

    return SEVERITY_ORDER.index(severity)


def __num_of_reports_to_fail(reports: list[Report],
                             fail_severity: str) -> int:
    """Number of reports at or above the given severity level."""
    threshold = SEVERITY_ORDER.index(fail_severity)
    return sum(1 for report in reports
               if __severity_rank(report.severity) >= threshold)


def __convert_reports(reports: list[Report],
                      repo_dir: str | None,
                      report_url: str | None,
                      changed_files: list[str],
                      changed_file_path: str | None,
                      *,
                      config: GerritConfig) -> dict:
    """Convert the given reports to gerrit json format.

    This function will convert the given reports to Gerrit json format.
    reports - list of reports comming from a plist file or
              from the CodeChecker server (both types can be processed)
    repo_dir - Root directory of the sources, i.e. the directory where the
               repository was cloned.
    report_url - URL where the report can be found something like this:
      "http://jenkins_address/userContent/$JOB_NAME/$BUILD_NUM/index.html"
    changed_files - list of the changed files
    changed_file_path - Path of the changed files json from Gerrit.
    config - Configuration of the review: the labels voted on and the
             severity level which makes the review fail.
    """
    review_comments: dict[str, list[dict]] = {}

    report_messages_in_unchanged_files = []
    for report in reports:
        file_name = report.file.path

        # file_name can be without a path in the report.
        if repo_dir \
                and os.path.dirname(file_name) != "" \
                and os.path.isabs(file_name):
            rel_file_path = os.path.relpath(file_name, repo_dir)
        else:
            rel_file_path = file_name

        checked_file = rel_file_path \
            + ':' + str(report.line) + ":" + str(report.column)

        review_comment_msg = \
            f"[{report.severity}] {checked_file}: {report.message} " \
            f"[{report.checker_name}]\n{report.source_line}"

        # Skip the report if it is not in the changed files.
        if changed_file_path and not \
                any(file_name.endswith(c) for c in changed_files):
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

    # Every report is sent as a comment but only the reports which reach the
    # configured severity level make the review fail. If no severity level is
    # configured then any report makes the review fail.
    if config.fail_severity is None:
        num_of_failing_reports = len(reports)
    else:
        num_of_failing_reports = __num_of_reports_to_fail(
            reports, config.fail_severity)

    review_failed = num_of_failing_reports > 0

    message = f"CodeChecker found {len(reports)} issue(s) in the code."

    if config.fail_severity is not None:
        if num_of_failing_reports:
            message += (f" {num_of_failing_reports} of them are at or above "
                        f"the '{config.fail_severity}' severity.")
        else:
            message += (" None of them are at or above the "
                        f"'{config.fail_severity}' severity.")

    if not config.labels:
        message += " No vote was cast."

    if report_messages_in_unchanged_files:
        message += ("\n\nThere following reports are introduced in files "
                    "which are not changed and can't be shown as individual "
                    "reports:\n{0}\n".format('\n'.join(
                        report_messages_in_unchanged_files)))

    if report_url:
        message += f" See: {report_url}"

    labels: dict[str, int] = {}
    for label in config.labels:
        labels[label.name] = \
            label.on_failure if review_failed else label.on_success

    review: dict[str, Any] = {"tag": config.tag,
                              "message": message}

    # A review without any vote is valid in Gerrit.
    if labels:
        review["labels"] = labels

    review["comments"] = review_comments

    return review


def __get_changed_files(changed_file_path: None | str) -> list[str]:
    """Return a list of changed files.

    Process the given gerrit changed file object and return a list of
    file paths which changed.

    The file can contain some garbage values at start, so we use regex
    to find a json object.
    """
    changed_files: list[str] = []

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
