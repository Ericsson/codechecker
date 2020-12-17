# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test getting git commit url. """


import unittest

from codechecker_server.api.report_server import get_commit_url
from codechecker_web.shared import webserver_context


class GetCommitUrlTestCase(unittest.TestCase):
    """
    Test cases to get commit url.
    """
    @classmethod
    def setup_class(cls):
        ctx = webserver_context.get_context()
        cls.__git_commit_urls = ctx.git_commit_urls

    def test_gerrit_url(self):
        """ Get commit url for a gerrit repository. """
        self.assertEqual(
            "https://gerrit.ericsson.se/"
            "gitweb?p=team/proj.git;a=commit;h=$commit",
            get_commit_url(
                'https://user@gerrit.ericsson.se/a/team/proj',
                self.__git_commit_urls))

        self.assertEqual(
            "https://gerrit.ericsson.se/"
            "gitweb?p=team/proj.git;a=commit;h=$commit",
            get_commit_url(
                'https://user@gerrit.ericsson.se/a/team/proj.git',
                self.__git_commit_urls))

    def test_bitbucket_url(self):
        """ Get commit url for a bitbucket repository. """
        self.assertEqual(
            "https://bitbucket.org/user/repo/commits/$commit",
            get_commit_url(
                'https://bitbucket.org/user/repo',
                self.__git_commit_urls))

        self.assertEqual(
            "https://bitbucket.org/user/repo/commits/$commit",
            get_commit_url(
                'https://bitbucket.org/user/repo.git',
                self.__git_commit_urls))

    def test_default_commit_url(self):
        """ Get commit url for default. """
        self.assertEqual(
            "https://default.org/user/repo/commit/$commit",
            get_commit_url(
                'https://default.org/user/repo',
                self.__git_commit_urls))

        self.assertEqual(
            "https://default.org/user/repo/commit/$commit",
            get_commit_url(
                'https://default.org/user/repo.git',
                self.__git_commit_urls))
