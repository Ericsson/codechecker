# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Parse the plist output of an analyzer and convert it to a report for
further processing.

With the newer clang releases more information is available in the plist files.

* Before Clang v3.7:
  - Checker name is misssing (tried to detect based on the description)
  - Report hash is not avilable (generated based on the report path elemens
    see report handling and plist parsing modules for more details.

* Clang v3.7:
  - Checker name is available in the plist
  - Report hash is still missing (hash is generated as before)

* After Clang v3.8:
  - Checker name is available
  - Report hash is available

* Clang-tidy:
  - No plist format is provided in the available releases (v3.9 and before)
  - Checker name can be parsed from the output
  - Report hash is generated based on the report path elements the same way as
    for Clang versions before v3.7

"""

import json
import os
import plistlib
import re
import sys
import traceback
from xml.parsers.expat import ExpatError

from libcodechecker.logger import LoggerFactory

from libcodechecker.report import Report
from libcodechecker.report import generate_report_hash

LOG = LoggerFactory.get_new_logger('PLIST_PARSER')


def levenshtein(a, b):  # http://hetland.org/coding/python/levenshtein.py
    """"Calculates the Levenshtein distance between a and b."""
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space.
        a, b = b, a
        n, m = m, n

    current = range(n+1)
    for i in range(1, m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1, n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)

    return current[n]


def checker_name_from_description(current_msg):
    """
    Try to find out the checker name based on the description
    provided by a checker.
    """

    # Clean message from variable and class name.
    clean_msg = re.sub(r"'.*?'", '', current_msg)

    closest_msg = ''
    min_dist = len(clean_msg) // 4

    message_map_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'checker_message_map.json')

    checker_message_map = {}
    with open(message_map_path) as map_file:
        checker_message_map = json.load(map_file)

    for msg in checker_message_map.keys():
        tmp_dist = levenshtein(clean_msg, msg)
        if tmp_dist < min_dist:
            closest_msg = msg
            min_dist = tmp_dist

    return checker_message_map[closest_msg]


def get_checker_name(diagnostic):
    """
    Check if checker name is available in the report.
    Checker name was not available in older clang versions before 3.7.
    """
    checker_name = diagnostic.get('check_name')
    if not checker_name:
        LOG.debug("Check name wasn't found in the plist file. "
                  "Read the user guide!")
        desc = diagnostic.get('description', '')
        checker_name = checker_name_from_description(desc)
        LOG.debug('Guessed check name: ' + checker_name)
    return checker_name


def get_report_hash(diagnostic, files):
    """
    Check if checker name is available in the report.
    Checker hash was not available in older clang versions before 3.8.
    """

    report_hash = diagnostic.get('issue_hash_content_of_line_in_context')
    if not report_hash:
        # Generate hash value if it is missing from the report.
        report_hash = generate_report_hash(diagnostic['path'], files,
                                           get_checker_name(diagnostic))
    return report_hash


def parse_plist(path):
    """
    Parse the reports from a plist file.
    One plist file can contain multiple reports.
    """
    LOG.debug("Parsing plist: " + path)

    reports = []
    files = []
    try:
        plist = plistlib.readPlist(path)

        files = plist['files']

        for diag in plist['diagnostics']:

            available_keys = diag.keys()

            main_section = {}
            for key in available_keys:
                # Skip path it is handled separately.
                if key != 'path':
                    main_section.update({key: diag[key]})

            # We need to extend information for plist files generated
            # by older clang version (before 3.7).
            main_section['check_name'] = get_checker_name(diag)

            # We need to extend information for plist files generated
            # by older clang version (before 3.8).
            main_section['issue_hash_content_of_line_in_context'] = \
                get_report_hash(diag, files)

            bug_path_items = [item for item in diag['path']]

            report = Report(main_section, bug_path_items)
            reports.append(report)

    except ExpatError as err:
        LOG.error('Failed to process plist file: ' + path +
                  ' wrong file format?')
        LOG.error(err)
    except AttributeError as ex:
        LOG.error('Failed to get important report data from plist.')
        LOG.error(ex)
    except IndexError as iex:
        LOG.error('Indexing error during processing plist file ' +
                  path)
        LOG.error(type(iex))
        LOG.error(repr(iex))
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
    except Exception as ex:
        LOG.error('Error during processing reports from the plist file: ' +
                  path)
        traceback.print_exc()
        LOG.error(type(ex))
        LOG.error(ex)
    finally:
        return files, reports
