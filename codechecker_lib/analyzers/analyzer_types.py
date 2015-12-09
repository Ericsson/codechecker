# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""
supported analyzer types
"""

CLANG_SA = 1
CLANG_TIDY = 2

analyzer_type_name_map = {'clangSA': CLANG_SA,
                          'clang-tidy': CLANG_TIDY}


def get_analyzer_type_name(type_value):
    """
    return the name for the analyzer type
    """
    for name, t_val in analyzer_type_name_map.iteritems():
        if t_val == type_value:
            return name
