# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Tests for checker handling."""


import unittest

from codechecker_analyzer.checkers import available


class TestCheckers(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        """Initialize a checkers list for the tests."""
        cls.__available_checkers = {"unix.Malloc",
                                    "core.DivideZero",
                                    "core.CallAndMessage",
                                    "readability-simd",
                                    "readability-else-after-return"}

    def test_checker_available(self):
        """Test for available checker."""
        ordered_checkers = [("unix.Malloc", True),
                            ("core.DivideZero", False)]
        missing_checkers = available(ordered_checkers,
                                     self.__available_checkers)
        self.assertSetEqual(missing_checkers, set())

    def test_profile_available(self):
        """Test for available profile."""
        profile_names = {"extreme", "sensitive"}
        checkers_with_profiles = self.__available_checkers
        checkers_with_profiles.update(profile_names)
        ordered_checkers = [("unix.Malloc", True),
                            ("core", True),
                            ("readability", False),
                            ("sensitive", True),
                            ("extreme", False)]
        missing_checkers = available(ordered_checkers,
                                     checkers_with_profiles)
        self.assertSetEqual(missing_checkers, set())

    def test_checker_not_available(self):
        """Test for missing checker."""
        ordered_checkers = [("unix.Malloc", True),
                            ("core.VLASize", True),
                            ("core.DivideZero", True),
                            ("cppcoreguidelines-avoid-goto", False),
                            ("Wc++11-extensions", False)]

        missing_checkers = available(ordered_checkers,
                                     self.__available_checkers)

        self.assertSetEqual(missing_checkers,
                            {"core.VLASize",
                             "cppcoreguidelines-avoid-goto",
                             "Wc++11-extensions"})

    def test_profile_not_available(self):
        """Test for missing profile."""
        profile_names = {"extreme", "sensitive"}
        checkers_with_profiles = self.__available_checkers
        checkers_with_profiles.update(profile_names)
        ordered_checkers = [("unix.Malloc", True),
                            ("core", True),
                            ("readability", False),
                            ("sensstive", True),
                            ("extremee", False)]
        missing_checkers = available(ordered_checkers,
                                     checkers_with_profiles)
        self.assertSetEqual(missing_checkers,
                            {"extremee", "sensstive"})
