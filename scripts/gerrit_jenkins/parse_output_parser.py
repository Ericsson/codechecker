# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Generates Gerrit Review json from CodeChecker parse's output.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import json
import os
import re
import sys


def parse_issue(issue, repo_dir, review):
    line = issue[0]
    abs_file_path = line[line.find(' ') + 1: line.find(':')]
    rel_file_path = os.path.relpath(abs_file_path, repo_dir)
    splitted = line.split(':')
    line_num = splitted[1]
    column_num = splitted[2]
    if rel_file_path not in review['comments']:
        review['comments'][rel_file_path] = []
    review['comments'][rel_file_path].append(
        {"range": {"start_line": line_num,
                   "start_character": column_num,
                   "end_line": line_num,
                   "end_character": column_num}, "message": ''.join(issue)})


def process_reports(repo_dir, reports, report_url):
    read = False
    issues = []
    # Matches the severity of the bug. If doesn't match, there is no report.
    severity = re.compile(r"^\[.*\]")
    for line in reports.readlines():
        if re.match(severity, line):
            read = True
            issues.append([line])
        elif line == '\n':
            read = False
        elif read:
            issues[-1].append(line)

    result = -1 if issues else 1
    report = ""
    if report_url:
        report = " Html report of the run is available at %s." % report_url
    review = {"tag": "jenkins",
              "message":
                  "CodeChecker found %i issue(s) in the code.%s"
                  % (len(issues), report),
              "labels": {"Code-Review": result, "Verified": 1}, "comments": {}}
    for issue in issues:
        parse_issue(issue, repo_dir, review)

    json.dump(review, sys.stdout)


def main():
    parser = argparse.ArgumentParser(
        description='Generates Gerrit Review json'
                    ' from CodeChecker parse\'s output.')
    parser.add_argument(
        'repo_dir',
        help="Root directory of the sources, \
              i.e. the directory where the repository was cloned.")
    parser.add_argument(
        '--report_url', nargs='?', default="",
        help="URL where the report can be found.")
    parser.add_argument(
        'parse_output', nargs='?', default=sys.stdin,
        type=argparse.FileType('r'),
        help="The output of CodeChecker parse. \
              If no file is provided, stdin is used.")
    args = parser.parse_args()

    process_reports(args.repo_dir, args.parse_output, args.report_url)


if __name__ == '__main__':
    main()
