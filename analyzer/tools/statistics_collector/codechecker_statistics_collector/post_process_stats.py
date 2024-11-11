# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Post-process statistical results.

Clang output files will be parsed for outputs by the statistics collector
checkers and converted into a special yml file which can be parsed back by the
statistics checkers.
"""

import logging
import os

from .collectors.return_value import ReturnValueCollector
from .collectors.special_return_value import SpecialReturnValueCollector

LOG = logging.getLogger('StatisticsCollector')


def process(input_dir, output_dir,
            stats_min_sample_count, stats_relevance_threshold):
    """
    Read the clang analyzer outputs where the statistics emitter checkers
    were enabled and collect the statistics.

    After the statistics collection cleanup the output files.
    """

    try:
        os.stat(output_dir)
    except Exception as ex:
        LOG.debug(ex)
        os.mkdir(output_dir)

    if not os.path.exists(input_dir):
        LOG.debug("No statistics directory was found")
        return

    clang_outs = []
    try:
        for f in os.listdir(input_dir):
            if os.path.isfile(os.path.join(input_dir, f)):
                clang_outs.append(os.path.join(input_dir, f))
    except OSError as oerr:
        LOG.debug(oerr)
        LOG.debug("Statistics can not be collected.")
        LOG.debug("Analyzer output error.")
        return

    if not clang_outs:
        LOG.warning("No output files were found to collect statistics.")
        return

    ret_collector = ReturnValueCollector(stats_min_sample_count,
                                         stats_relevance_threshold)
    special_ret_collector =\
        SpecialReturnValueCollector(stats_min_sample_count,
                                    stats_relevance_threshold)

    lines = set()
    for clang_output in clang_outs:
        with open(clang_output, 'r',
                  encoding='utf-8', errors='ignore') as out:
            lines |= set(out.readlines())
    for line in lines:
        ret_collector.process_line(line)
        special_ret_collector.process_line(line)
    LOG.debug("Collecting statistics finished.")

    # Write out statistics.
    unchecked_yaml = ReturnValueCollector.stats_file(output_dir)
    LOG.debug("Writing out statistics to %s", unchecked_yaml)
    with open(unchecked_yaml, 'w',
              encoding='utf-8', errors='ignore') as uyaml:
        uyaml.write(ret_collector.get_yaml())

    special_ret_yaml = SpecialReturnValueCollector.stats_file(output_dir)
    LOG.debug("Writing out statistics to %s", special_ret_yaml)
    with open(special_ret_yaml, 'w',
              encoding='utf-8', errors='ignore') as uyaml:
        uyaml.write(special_ret_collector.get_yaml())
