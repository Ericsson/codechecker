# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

class DBVersionInfo(object):

    def __init__(self, major, minor):
        self.major = major
        self.minor = minor

    def is_compatible(self, major, minor):
        return major != self.major

    def get_expected_version(self):
        return (self.major, self.minor)

DB_VERSION_INFO = DBVersionInfo(1, 0)
