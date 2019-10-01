# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


class VersionInfo(object):
    """VersionInfo holds the version information for a static analyzer."""

    def __init__(self,
                 major_version=None,
                 minor_version=None,
                 patch_version=None,
                 installed_dir="",
                 vendor="",
                 cmd_output=""):

        self.major_version = \
            int(major_version) if major_version else major_version
        self.minor_version = \
            int(minor_version) if minor_version else minor_version
        self.patch_version = \
            int(patch_version) if patch_version else patch_version
        self.installed_dir = installed_dir
        self.cmd_output = cmd_output
        self.vendor = vendor
