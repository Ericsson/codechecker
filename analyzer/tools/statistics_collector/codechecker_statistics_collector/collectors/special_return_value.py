# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Special return value statistics collector. """

from io import StringIO

from collections import defaultdict
import os
import re


class SpecialReturnValueCollector:
    """ Collect special return value statistics.

    This script lists functions of which the return value is checked for
    negative (integers) or null (pointers).
    """

    # Checker name used for pre analysis.
    checker_collect = 'statisticscollector.SpecialReturnValue'

    # Checker name which runs the analysis.
    checker_analyze = 'statisticsbased.SpecialReturnValue'

    def __init__(self, stats_min_sample_count, stats_relevance_threshold):
        self.stats_min_sample_count = stats_min_sample_count
        self.stats_relevance_threshold = stats_relevance_threshold

        # Matching these lines:
        # /.../x.c:551:12: warning:
        # Special Return Value:/.../x.c:551:12,parsedate,0,0

        ptrn = \
            r'.*warning: Special Return Value:'\
            '.*:[0-9]*:[0-9]*.*,(.*),([0,1]),([0,1])'
        self.special_ret_val_regexp = re.compile(ptrn)

        self.stats = {'total': defaultdict(int),
                      'nof_negative': defaultdict(int),
                      'nof_null': defaultdict(int)}

    @staticmethod
    def stats_file(path):
        return os.path.join(path, 'SpecialReturn.yaml')

    @staticmethod
    def checker_analyze_cfg(path):
        """ Return the checker config parameter for the analyzer checker. """
        return ['-Xclang', '-analyzer-config',
                '-Xclang',
                'alpha.ericsson.statisticsbased:APIMetadataPath=' + path]

    def total(self):
        return self.stats.get('total')

    def nof_null(self):
        return self.stats.get('nof_null')

    def nof_negative(self):
        return self.stats.get('nof_negative')

    def process_line(self, line):
        """ Match regex on the line. """
        m = self.special_ret_val_regexp.match(line)
        if m:
            func = m.group(1)
            ret_negative = m.group(2)
            ret_null = m.group(3)

            self.stats['total'][func] += 1
            self.stats['nof_negative'][func] += int(ret_negative)
            self.stats['nof_null'][func] += int(ret_null)

    def filter_stats(self):
        """ Filter the collected statistics based on the threshold. """
        neg = []
        null = []
        stats = self.stats
        total = stats.get('total')

        for key in sorted(stats.get('total').keys()):
            negative_ratio = stats['nof_negative'][key]/stats['total'][key]
            if (self.stats_relevance_threshold < negative_ratio < 1 and
                    total[key] >= self.stats_min_sample_count):
                neg.append(key)

            null_ratio = stats['nof_null'][key]/stats['total'][key]
            if (self.stats_relevance_threshold < null_ratio < 1 and
                    total[key] >= self.stats_min_sample_count):
                null.append(key)
        return neg, null

    def get_yaml(self):
        """ Get statistics in yaml format.

        FIXME proper yaml generation.
        """
        stats_yaml = StringIO()

        stats_yaml.write("#\n")
        stats_yaml.write("# SpecialReturn metadata format 1.0\n")
        neg, null = self.filter_stats()

        for n in neg:
            stats_yaml.write(
                "{name: " + n + ", relation: LT, value: 0}\n")
        for n in null:
            stats_yaml.write(
                "{name: " + n + ", relation: EQ, value: 0}\n")

        return stats_yaml.getvalue()
