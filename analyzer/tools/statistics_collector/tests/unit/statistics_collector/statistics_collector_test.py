# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Unit tests for the statistics_collectors module. """


import unittest

from codechecker_statistics_collector.collectors.special_return_value import \
    SpecialReturnValueCollector
from codechecker_statistics_collector.collectors.return_value import \
    ReturnValueCollector


class statisticsCollectorTest(unittest.TestCase):
    """ Testing the statistics collectors output parsing. """

    def test_spec_ret_val_coll(self):
        """
        Parse the output of the special return value collector checker.
        """
        test_input = ["/.../x.c:551:12: warning:"
                      " Special Return Value:/.../x.c:551:12,parsedate,0,0",
                      "/.../x.c:551:12: warning:"
                      " Special Return Value:/.../x.c:551:12,parsedate,0,0",
                      "/.../x.c:551:12: warning:"
                      " Special Return Value:/.../x.c:551:12,parsedate,0,0",
                      "/.../x.c:551:12: warning:"
                      " Special Return Value:/.../x.c:551:12,parsedate,0,0"
                      ]

        special_ret_collector = SpecialReturnValueCollector(10, 0.85)

        for line in test_input:
            special_ret_collector.process_line(line)

        self.assertEqual({'parsedate': 4}, special_ret_collector.total())
        self.assertEqual({'parsedate': 0}, special_ret_collector.nof_null())
        self.assertEqual({'parsedate': 0},
                         special_ret_collector.nof_negative())

    def test_spec_ret_val_coll_neg_filter(self):
        """
        Parse the output of the special return value collector checker
        with more various return value output
        (number of null return, number of negative returns)
        with filtering based on the threshold.
        """

        test_ret_neg = ["/.../x.c:551:12: warning:"
                        " Special Return Value:/.../x.c:551:12,parsedate,1,0",
                        "/.../x.c:551:12: warning:"
                        " Special Return Value:/.../x.c:551:12,parsedate,0,1",
                        "/.../x.c:551:12: warning:"
                        " Special Return Value:/.../x.c:551:12,parsedate,1,1",
                        "/.../x.c:551:12: warning:"
                        " Special Return Value:/.../x.c:551:12,parsedate,1,1",
                        "/.../x.c:551:12: warning:"
                        " Special Return Value:/.../x.c:551:12,parsedate,1,1",
                        "/.../x.c:551:12: warning:"
                        " Special Return Value:/.../x.c:551:12,parsedate,1,1",
                        "/.../x.c:551:12: warning:"
                        " Special Return Value:/.../x.c:551:12,parsedate,1,1",
                        "/.../x.c:551:12: warning:"
                        " Special Return Value:/.../x.c:551:12,parsedate,1,1",
                        "/.../x.c:551:12: warning:"
                        " Special Return Value:/.../x.c:551:12,parsedate,1,1",
                        "/.../x.c:551:12: warning:"
                        " Special Return Value:/.../x.c:551:12,parsedate,1,1",
                        "/.../x.c:552:14: warning:"
                        " Special Return Value:/.../x.c:551:12,myfunc,0,0",
                        "/.../x.c:552:14: warning:"
                        " Special Return Value:/.../x.c:551:12,myfunc,0,0",
                        "/.../x.c:552:14: warning:"
                        " Special Return Value:/.../x.c:551:12,myfunc,0,0",
                        "/.../x.c:552:14: warning:"
                        " Special Return Value:/.../x.c:551:12,myfunc,0,0",
                        "/.../x.c:552:14: warning:"
                        " Special Return Value:/.../x.c:551:12,myfunc,0,0",
                        "/.../x.c:552:14: warning:"
                        " Special Return Value:/.../x.c:551:12,myfunc,0,0",
                        ]

        special_ret_collector = SpecialReturnValueCollector(10, 0.85)

        for line in test_ret_neg:
            special_ret_collector.process_line(line)

        self.assertEqual({'parsedate': 10, 'myfunc': 6},
                         special_ret_collector.total())
        self.assertEqual({'parsedate': 9, 'myfunc': 0},
                         special_ret_collector.nof_null())
        self.assertEqual({'parsedate': 9, 'myfunc': 0},
                         special_ret_collector.nof_negative())
        self.assertEqual((['parsedate'], ['parsedate']),
                         special_ret_collector.filter_stats())

    def test_ret_val_coll_neg(self):
        """
        Test return value statistics collector output parsing.
        """
        test_ret_neg = ["/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,1",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,1",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        ]

        ret_val_collector = ReturnValueCollector(10, 0.85)

        for line in test_ret_neg:
            ret_val_collector.process_line(line)

        self.assertEqual({'parsedate': 6}, ret_val_collector.total())
        self.assertEqual({'parsedate': 2}, ret_val_collector.nof_unchecked())

    def test_ret_val_coll_filtering(self):
        """
        Test the statistics collectors output parsing and
        filtering based on the default threshold.
        """
        test_ret_neg = ["/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,0",
                        "/.../x.c:551:12: warning:"
                        " Return Value Check:/.../x.c:551:12,parsedate,1",
                        ]

        ret_val_collector = ReturnValueCollector(10, 0.85)

        for line in test_ret_neg:
            ret_val_collector.process_line(line)

        self.assertEqual({'parsedate': 10}, ret_val_collector.total())
        self.assertEqual({'parsedate': 1}, ret_val_collector.nof_unchecked())
        self.assertEqual(['parsedate'], ret_val_collector.filter_stats())
