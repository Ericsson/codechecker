# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import re


def available(ordered_checkers, available_checkers):
    """Verify if every element in the ordered checkers a valid checker name.

    Every element in the ordered checkers should match partially
    a checker or profile name in available_checkers.

    Returns the set of checker names without any match.
    """
    missing_checkers = set()
    for checker in ordered_checkers:
        checker_name, _ = checker
        name_match = False
        for available_checker in available_checkers:
            regex = "^" + str(checker_name) + ".*$"
            c_name = available_checker
            match = re.match(regex, c_name)
            if match:
                name_match = True
                break

        if not name_match:
            missing_checkers.add(checker_name)
    return missing_checkers
