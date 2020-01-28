# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from ..plist_converter import PlistConverter


class SpotBugsPlistConverter(PlistConverter):
    """ SpotBugs plist converter. """

    def _create_diag(self, message, files):
        """ Creates a new plist diagnostic from the given message. """
        diag = super(SpotBugsPlistConverter, self) \
            ._create_diag(message, files)
        diag['orig_issue_hash_content_of_line_in_context'] = \
            message.report_hash

        return diag
