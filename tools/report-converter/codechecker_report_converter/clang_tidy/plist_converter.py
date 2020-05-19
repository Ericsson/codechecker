# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


from ..plist_converter import PlistConverter


class ClangTidyPlistConverter(PlistConverter):
    """ Warning messages to plist converter. """

    def _get_checker_category(self, checker):
        """ Returns the check's category."""
        parts = checker.split('-')
        return parts[0] if parts else 'unknown'
