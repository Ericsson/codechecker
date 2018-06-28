# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""
Calculates call statistics from analysis output
"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from StringIO import StringIO
from collections import defaultdict
import os
import re

from libcodechecker.analyze.analyzer_env import\
    extend_analyzer_cmd_with_resource_dir

from libcodechecker.logger import get_logger

LOG = get_logger('analyzer')


def build_stat_coll_cmd(action, config, source, environ):
    """
    Build the statistics collector analysis command.
    """

    cmd = [config.analyzer_binary]
    cmd.append('-c')
    cmd.extend(['-x', action.lang])

    # Do not warn about the unused gcc/g++ arguments.
    cmd.append('-Qunused-arguments')

    cmd.append('--analyze')

    for plugin in config.analyzer_plugins:
        cmd.extend(["-Xclang", "-plugin",
                    "-Xclang", "checkercfg",
                    "-Xclang", "-load",
                    "-Xclang", plugin])

    # Enable text only output for later parsing.
    analyzer_mode = 'text'
    cmd.extend(['-Xclang',
                '-analyzer-opt-analyze-headers',
                '-Xclang',
                '-analyzer-output=' + analyzer_mode])

    cmd.append(config.analyzer_extra_arguments)
    cmd.extend(action.analyzer_options)

    # Enable the statistics collector checkers only.
    collector_checkers = []
    for checker_name, _ in config.checks().items():
        if SpecialReturnValueCollector.checker_collect in checker_name:
            collector_checkers.append(checker_name)

        if ReturnValueCollector.checker_collect in checker_name:
            collector_checkers.append(checker_name)

    if not collector_checkers:
        LOG.debug('No available statistics collector checkers were found')
        return [], False

    for coll_check in collector_checkers:
        cmd.extend(['-Xclang',
                    '-analyzer-checker=' + coll_check])

    if action.target != "":
        cmd.append("--target=" + action.target)
    extend_analyzer_cmd_with_resource_dir(cmd,
                                          config.compiler_resource_dir)
    cmd.extend(action.compiler_includes)

    if source:
        cmd.append(source)
    return cmd, True


class SpecialReturnValueCollector(object):
    """
    Collect special return value statistics.

    This script lists functions of which the return

    value is checked for negative (integers) or null (pointers).
    """

    # Checker name used for pre analysis.
    checker_collect = 'statisticscollector.SpecialReturnValue'

    # Checker name which runs the analysis.
    checker_analyze = 'statisticsbased.SpecialReturnValue'

    def __init__(self):
        # Matching these lines
        """"/.../x.c:551:12: warning:
            Special Return Value:/.../x.c:551:12,parsedate,0,0
        """
        ptrn = \
            r'.*Special Return Value:.*:[0-9]*:[0-9]*.*,(.*),([0,1]),([0,1])'
        self.special_ret_val_regexp = re.compile(ptrn)

        # collected statistics
        self.stats = {
                'total': defaultdict(int),
                'nof_negative': defaultdict(int),
                'nof_null': defaultdict(int)
                }

    @staticmethod
    def stats_file(path):
        return os.path.join(path, 'SpecialReturn.yaml')

    @staticmethod
    def checker_analyze_cfg(path):
        """
        Return the checker config parameter for the analyzer checker.
        """
        if not os.path.exists(SpecialReturnValueCollector.stats_file(path)):
            LOG.debug('No checker statistics file was found for ' +
                      SpecialReturnValueCollector.checker_analyze)
            return []
        else:
            return ['-Xclang', '-analyzer-config',
                    '-Xclang', 'api-metadata-path=' + path]

    def total(self):
        return self.stats.get('total')

    def nof_null(self):
        return self.stats.get('nof_null')

    def nof_negative(self):
        return self.stats.get('nof_negative')

    def process_line(self, line):
        """
        Match regex on the line
        """
        m = self.special_ret_val_regexp.match(line)
        if m:
            func = m.group(1)
            ret_negative = m.group(2)
            ret_null = m.group(3)

            self.stats['total'][func] += 1
            self.stats['nof_negative'][func] += int(ret_negative)
            self.stats['nof_null'][func] += int(ret_null)

    def filter_stats(self, threshold=0.85, min_occurence_count=1):

        neg = []
        null = []
        stats = self.stats
        total = stats.get('total')

        if threshold > 1:
            LOG.warning("Statistics threshold should be under 1")

        for key in sorted(stats.get('total').keys()):

            negative_ratio = stats['nof_negative'][key]/stats['total'][key]
            if (threshold < negative_ratio < 1 and
                    total[key] >= min_occurence_count):
                neg.append(key)

            null_ratio = stats['nof_null'][key]/stats['total'][key]
            if (threshold < null_ratio < 1 and
                    total[key] >= min_occurence_count):
                null.append(key)

        return neg, null

    def get_yaml(self):
        """
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


class ReturnValueCollector(object):
    """
    Collect return value statistics.
    This script lists functions of which the return value is mostly checked.
    """

    # Checker name used for pre analysis.
    checker_collect = 'statisticscollector.ReturnValueCheck'

    # Checker name which runs the analysis.
    checker_analyze = 'statisticsbased.UncheckedReturnValue'

    def __init__(self):

        # Matching these lines
        """
        /.../x.c:551:12:
        warning: Return Value Check:/.../x.c:551:12,parsedate,0
        """

        self.ret_val_regexp = \
            re.compile(r'.*Return Value Check:.*:[0-9]*:[0-9]*.*,(.*),([0,1])')

        self.stats = {'total': defaultdict(int),
                      'nof_unchecked': defaultdict(int)}

    @staticmethod
    def stats_file(path):
        return os.path.join(path, 'UncheckedReturn.yaml')

    @staticmethod
    def checker_analyze_cfg(path):
        """
        Return the checker config parameter for the analyzer checker.
        """
        if not os.path.exists(ReturnValueCollector.stats_file(path)):
            LOG.debug('No checker statistics file was found for ' +
                      ReturnValueCollector.checker_analyze)
            return []
        else:
            return ['-Xclang', '-analyzer-config',
                    '-Xclang', 'api-metadata-path=' + path]

    def total(self):
        return self.stats.get('total')

    def nof_unchecked(self):
        return self.stats.get('nof_unchecked')

    def unchecked(self):
        return self.stats.get('unchecked')

    def process_line(self, line):
        """
        Match regex on the line
        """
        m = self.ret_val_regexp.match(line)
        if m:
            func = m.group(1)
            checked = m.group(2)
            self.stats['total'][func] += 1
            self.stats['nof_unchecked'][func] += int(checked)

    def filter_stats(self, threshold=0.85, min_occurence_count=1):
        """
        Filter the collected statistics based on the threshold.
        Return a lisf of function names where the return value
        was unchecked above the threshold.
        """
        if threshold > 1:
            LOG.warning("Statistics threshold should be under 1")

        unchecked_functions = []
        total = self.stats.get('total')
        for key in sorted(total):
            checked_ratio = 1 - \
                    self.stats['nof_unchecked'][key]/self.stats['total'][key]
            if (threshold < checked_ratio < 1 and
                    total[key] >= min_occurence_count):
                unchecked_functions.append(key)
        return unchecked_functions

    def get_yaml(self):
        """
        FIXME proper yaml generation.
        """
        stats_yaml = StringIO()

        stats_yaml.write("#\n")
        stats_yaml.write("# UncheckedReturn metadata format 1.0\n")
        for function_name in self.filter_stats():
            stats_yaml.write("- " + function_name + '\n')

        return stats_yaml.getvalue()


def postprocess_stats(clang_output_dir, stats_dir):
    """
    Read the clang analyzer outputs where the statistics emitter checkers
    were enabled and collect the statistics.

    After the statistics collection cleanup the output files.
    """

    # Statistics yaml files will be stored in stats_dir
    try:
        os.stat(stats_dir)
    except Exception as ex:
        LOG.debug(ex)
        os.mkdir(stats_dir)

    if not os.path.exists(clang_output_dir):
        LOG.debug("No statistics directory was found")
        return

    clang_outs = []
    try:
        for f in os.listdir(clang_output_dir):
            if os.path.isfile(os.path.join(clang_output_dir, f)):
                clang_outs.append(os.path.join(clang_output_dir, f))
    except OSError as oerr:
        LOG.debug(oerr)
        LOG.debug("Statistics can not be collected.")
        LOG.debug("Analyzer output error.")
        return

    if not len(clang_outs):
        LOG.warning("No output files were found to collect statistics.")
        return

    ret_collector = ReturnValueCollector()
    special_ret_collector = SpecialReturnValueCollector()

    for clang_output in clang_outs:
        with open(clang_output, 'r') as out:
            for line in out:
                ret_collector.process_line(line)
                special_ret_collector.process_line(line)

    LOG.debug("Collecting statistics finished.")

    # Write out statistics.
    unchecked_yaml = ReturnValueCollector.stats_file(stats_dir)
    LOG.debug("Writing out statistics to " + unchecked_yaml)
    with open(unchecked_yaml, 'w') as uyaml:
        uyaml.write(ret_collector.get_yaml())

    special_ret_yaml = SpecialReturnValueCollector.stats_file(stats_dir)
    LOG.debug("Writing out statistics to " + special_ret_yaml)
    with open(special_ret_yaml, 'w') as uyaml:
        uyaml.write(special_ret_collector.get_yaml())
