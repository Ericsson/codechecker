# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Return value statistics collector. """

from io import StringIO
from collections import defaultdict
import os
import re


class ReturnValueCollector:
    """ Collect return value statistics.

    This script lists functions of which the return value is mostly checked.
    """

    # Checker name used for pre analysis.
    checker_collect = 'statisticscollector.ReturnValueCheck'

    # Checker name which runs the analysis.
    checker_analyze = 'statisticsbased.UncheckedReturnValue'

    def __init__(self, stats_min_sample_count, stats_relevance_threshold):
        self.stats_min_sample_count = stats_min_sample_count
        self.stats_relevance_threshold = stats_relevance_threshold

        # Matching these lines:
        # /.../x.c:551:12:
        # warning: Return Value Check:/.../x.c:551:12,parsedate,0

        self.ret_val_regexp = \
            re.compile(r'.*warning: Return Value Check:'
                       '.*:[0-9]*:[0-9]*.*,(.*),([0,1])')

        self.stats = {'total': defaultdict(int),
                      'nof_unchecked': defaultdict(int)}

    @staticmethod
    def stats_file(path):
        return os.path.join(path, 'UncheckedReturn.yaml')

    @staticmethod
    def checker_analyze_cfg(path):
        """ Return the checker config parameter for the analyzer checker. """
        return ['-Xclang', '-analyzer-config',
                '-Xclang',
                'alpha.ericsson.statisticsbased:APIMetadataPath=' + path]

    def total(self):
        return self.stats.get('total')

    def nof_unchecked(self):
        return self.stats.get('nof_unchecked')

    def unchecked(self):
        return self.stats.get('unchecked')

    def process_line(self, line):
        """ Match regex on the line """
        m = self.ret_val_regexp.match(line)
        if m:
            func = m.group(1)
            checked = m.group(2)
            self.stats['total'][func] += 1
            self.stats['nof_unchecked'][func] += int(checked)

    def filter_stats(self):
        """ Filter the collected statistics based on the threshold.

        Return a lisf of function names where the return value
        was unchecked above the threshold.
        """
        unchecked_functions = []
        total = self.stats.get('total')
        for key in sorted(total):
            checked_ratio = 1 - \
                    self.stats['nof_unchecked'][key]/self.stats['total'][key]
            if (self.stats_relevance_threshold < checked_ratio < 1 and
                    self.stats['total'][key] >= self.stats_min_sample_count):
                unchecked_functions.append(key)
        return unchecked_functions

    def get_yaml(self):
        """ Get statistics in yaml format.

        FIXME proper yaml generation.
        """
        stats_yaml = StringIO()

        stats_yaml.write("#\n")
        stats_yaml.write("# UncheckedReturn metadata format 1.0\n")
        for function_name in self.filter_stats():
            stats_yaml.write("- " + function_name + '\n')

        return stats_yaml.getvalue()
