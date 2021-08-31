# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import re


def available(ordered_checkers, available_checkers):
    """Verify if every element in the ordered checkers a valid checker name.

    Every element in the ordered checkers should match partially
    a checker or profile name in available_checkers.

    Returns the set of checker names without any match.
    """
    missing_checkers = set()
    for checker_name, _ in ordered_checkers:
        # TODO: This label list shouldn't be hard-coded here.
        if checker_name.startswith('profile:') or \
                checker_name.startswith('guideline:') or \
                checker_name.startswith('severity:') or \
                checker_name.startswith('sei-cert:'):
            continue

        name_match = False
        for available_checker in available_checkers:
            regex = "^" + re.escape(str(checker_name)) + ".*$"
            c_name = available_checker
            match = re.match(regex, c_name)
            if match:
                name_match = True
                break

        if not name_match:
            missing_checkers.add(checker_name)
    return missing_checkers
