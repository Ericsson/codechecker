# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

class DBVersionInfo(object):

    def __init__(self, major, minor):
        self.major = int(major)
        self.minor = int(minor)

    def is_compatible(self, major, minor):
        return major != self.major

    def get_expected_version(self):
        return (self.major, self.minor)

    def __str__(self):
        return 'v'+str(self.major)+'.'+str(self.minor)
