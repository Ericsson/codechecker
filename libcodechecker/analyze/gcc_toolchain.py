# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""
gcc-toolchain compilation option related helper functions.
"""

import os
import re


def toolchain_in_args(compiler_option):
    """
    Check for the --gcc-toolchain in the compilation options.

    """
    for cmp_opt in compiler_option:
        if '--gcc-toolchain' in cmp_opt:
            tcpath = \
                re.match(r"^--gcc-toolchain=(?P<tcpath>.*)$",
                         cmp_opt).group('tcpath')
            return tcpath

    return None


def get_toolchain_compiler(toolchain_path, language):
    """
    The compiler binary is expected to be under the bin directory
    in the tooolchain path.

    Construct the binary path base on the compilation language.
    """

    if language == 'c':
        return os.path.join(toolchain_path, 'bin', 'gcc')
    elif language == 'c++':
        return os.path.join(toolchain_path, 'bin', 'g++')

    return None
