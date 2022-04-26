# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Run pre analysis, collect statistics or CTU data.
"""

import multiprocessing
import os
import shlex
import shutil
import signal
import sys
import traceback
import uuid

from codechecker_analyzer import env
from codechecker_common.logger import get_logger

from codechecker_statistics_collector import post_process_stats

from .analyzers import analyzer_base
from .analyzers.clangsa import ctu_manager, ctu_triple_arch
from .analyzers.clangsa import statistics
from .analyzers.clangsa.analyzer import ClangSA

LOG = get_logger('analyzer')


def collect_statistics(action, source, clangsa_config,
                       environ, statistics_data):
    """
    Run the statistics collection command and save the
    stdout and stderr to a file.
    """
    cmd, can_collect = statistics.build_stat_coll_cmd(action, clangsa_config,
                                                      source)

    if not can_collect:
        LOG.debug('Can not collect statistical data.')
        return

    # TODO: shlex.join() will be more convenient in Python 3.8.
    LOG.debug_analyzer(' '.join(map(shlex.quote, cmd)))

    ret_code, analyzer_out, analyzer_err = \
        analyzer_base.SourceAnalyzer.run_proc(cmd, env=environ)

    LOG.debug(analyzer_out)
    LOG.debug(analyzer_err)
    if ret_code:
        LOG.error("Failed to collect statistics for %s", source)
        return ret_code

    LOG.debug("Running statistics collectors for %s was sucesssful.",
              source)

    _, source_filename = os.path.split(source)

    output_id = source_filename + str(uuid.uuid4()) + '.stat'

    stat_for_source = os.path.join(statistics_data['stat_tmp_dir'],
                                   output_id)

    with open(stat_for_source, 'w', encoding="utf-8", errors="ignore") as out:
        out.write(analyzer_out)
        out.write(analyzer_err)

    return ret_code


# Progress reporting.
progress_checked_num = None
progress_actions = None


def init_worker(checked_num, action_num):
    global progress_checked_num, progress_actions
    progress_checked_num = checked_num
    progress_actions = action_num


def pre_analyze(params):
    action, context, clangsa_config, skip_handlers, \
        ctu_data, statistics_data = params

    analyzer_environment = env.extend(context.path_env_extra,
                                      context.ld_lib_path_extra)

    progress_checked_num.value += 1

    if skip_handlers and skip_handlers.should_skip(action.source):
        return
    if action.analyzer_type != ClangSA.ANALYZER_NAME:
        return

    _, source_filename = os.path.split(action.source)

    LOG.info("[%d/%d] %s",
             progress_checked_num.value,
             progress_actions.value, source_filename)

    try:
        if ctu_data:
            LOG.debug("running CTU pre analysis")
            ctu_temp_fnmap_folder = ctu_data.get('ctu_temp_fnmap_folder')
            ctu_func_map_cmd = ctu_data.get('ctu_func_map_cmd')

            triple_arch = \
                ctu_triple_arch.get_triple_arch(action, action.source,
                                                clangsa_config,
                                                analyzer_environment)

            # TODO: reorganize the various ctu modes parameters
            # Dump-based analysis requires serialized ASTs.
            if clangsa_config.ctu_on_demand:
                ctu_manager.generate_invocation_list(triple_arch, action,
                                                     action.source,
                                                     clangsa_config,
                                                     analyzer_environment)
            else:
                ctu_manager.generate_ast(triple_arch, action, action.source,
                                         clangsa_config, analyzer_environment)
            # On-demand analysis does not require AST-dumps.
            # We map the function names to corresponding sources of ASTs.
            # In case of On-demand analysis this source is the original source
            # code. In case of AST-dump based analysis these sources are the
            # generated AST-dumps.
            ctu_manager.map_functions(triple_arch, action, action.source,
                                      clangsa_config, analyzer_environment,
                                      ctu_func_map_cmd,
                                      ctu_temp_fnmap_folder)

    except Exception as ex:
        LOG.debug_analyzer(str(ex))
        traceback.print_exc(file=sys.stdout)
        raise

    try:
        if statistics_data:
            LOG.debug("running statistics pre analysis")
            collect_statistics(action,
                               action.source,
                               clangsa_config,
                               analyzer_environment,
                               statistics_data)

    except Exception as ex:
        LOG.debug_analyzer(str(ex))
        traceback.print_exc(file=sys.stdout)
        raise


def run_pre_analysis(actions, context, clangsa_config,
                     jobs, skip_handlers, ctu_data, statistics_data, manager):
    """
    Run multiple pre analysis jobs before the actual analysis.
    """
    LOG.info('Pre-analysis started.')
    if ctu_data:
        LOG.info("Collecting data for ctu analysis.")
    if statistics_data:
        LOG.info("Collecting data for statistical analysis.")

    def signal_handler(signum, frame):
        try:
            pool.terminate()
            manager.shutdown()
        finally:
            sys.exit(128 + signum)

    signal.signal(signal.SIGINT, signal_handler)

    processed_var = multiprocessing.Value('i', 0)
    actions_num = multiprocessing.Value('i', len(actions))

    pool = multiprocessing.Pool(jobs,
                                initializer=init_worker,
                                initargs=(processed_var,
                                          actions_num))

    if statistics_data:
        # Statistics collection is enabled setup temporary
        # directories.
        stat_tmp_dir = statistics_data['stat_tmp_dir']

        # Cleaning previous outputs.
        if os.path.exists(stat_tmp_dir):
            shutil.rmtree(stat_tmp_dir)

        os.makedirs(stat_tmp_dir)

    try:
        collect_actions = [(build_action,
                            context,
                            clangsa_config,
                            skip_handlers,
                            ctu_data,
                            statistics_data)
                           for build_action in actions]
        # FIXME: Ensure all shared data structures are wrapped in manager
        #        proxy objects before passing them to other processes via
        #        map_async.
        #        Note that even deep-copying is known to be insufficient.
        pool.map_async(pre_analyze, collect_actions)
        pool.close()
    except Exception:
        pool.terminate()
        raise
    finally:
        pool.join()

    # Postprocessing the pre analysis results.
    if ctu_data:
        ctu_manager.merge_clang_extdef_mappings(
                ctu_data.get('ctu_dir'),
                ctu_data.get('ctu_func_map_file'),
                ctu_data.get('ctu_temp_fnmap_folder'))

    if statistics_data:

        stats_in = statistics_data.get('stat_tmp_dir')
        stats_out = statistics_data.get('stats_out_dir')

        post_process_stats.process(stats_in, stats_out,
                                   statistics_data.get(
                                      'stats_min_sample_count'),
                                   statistics_data.get(
                                      'stats_relevance_threshold'))

        if os.path.exists(stats_in):
            LOG.debug('Cleaning up temporary statistics directory')
            shutil.rmtree(stats_in)
    LOG.info('Pre-analysis finished.')
