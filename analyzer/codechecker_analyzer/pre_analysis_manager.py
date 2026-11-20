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

import glob
import os
import shlex
import shutil
import signal
import sys
import traceback
import uuid
import zipfile

import multiprocess  # type: ignore

from codechecker_common.logger import get_logger

from codechecker_statistics_collector import post_process_stats

from tu_collector import tu_collector

from .analyzers import analyzer_base
from .analyzers.clangsa import ctu_manager, ctu_triple_arch
from .analyzers.clangsa import statistics
from .analyzers.clangsa.analyzer import ClangSA
from .util import analyzer_action_hash
from typing import Any

LOG = get_logger('analyzer')


def ctu_collect_zip_prefix(action):
    """
    The common file name prefix of the CTU collect failure archives of the
    given build action. It matches the name of the action's analysis result
    file, so the archive can be paired with it.
    """
    action_hash = analyzer_action_hash(action.source, action.directory,
                                       action.original_command)
    return f"{os.path.basename(action.source)}_{ClangSA.ANALYZER_NAME}_" \
        f"{action_hash}_ctu_collect_"


def remove_ctu_collect_zips(action, failed_dir):
    """
    Remove the CTU collect failure archives of a previous run of the given
    build action, so that stale failures are not kept.
    """
    pattern = glob.escape(os.path.join(failed_dir,
                                       ctu_collect_zip_prefix(action)))
    for zip_file in glob.glob(pattern + '*.zip'):
        os.remove(zip_file)


def save_ctu_collect_failure(action, failure, output_path):
    """
    Pack a debug archive about a failed CTU collect step into the failed
    directory, similarly to the archives of failed analyses.
    """
    ret_code = failure['returncode']
    if failure['step'] == 'exception':
        failure_type = ''
    elif ret_code == 254 or ret_code < 0:
        failure_type = '_crash'
    else:
        failure_type = '_error'

    failed_dir = os.path.join(output_path, 'failed')
    os.makedirs(failed_dir, exist_ok=True)

    zip_file = os.path.join(
        failed_dir,
        ctu_collect_zip_prefix(action) + failure['step'] + failure_type +
        '.zip')

    try:
        tu_collector.zip_tu_files(zip_file, [{
            'file': action.source,
            'command': action.original_command,
            'directory': action.directory}])
    except Exception as ex:
        LOG.debug("Couldn't collect the sources of %s into %s: %s",
                  action.source, zip_file, str(ex))

    with zipfile.ZipFile(zip_file, 'a') as archive:
        archive.writestr("stdout", failure['stdout'] or '')
        archive.writestr("stderr", failure['stderr'] or '')
        archive.writestr("build-action", action.original_command)
        archive.writestr("analyzer-command", shlex.join(failure['cmd']))
        archive.writestr("return-code", str(ret_code))

        compiler_info_file = os.path.join(output_path, 'compiler_info.json')
        if os.path.exists(compiler_info_file):
            archive.write(compiler_info_file, "compiler_info.json")

    LOG.debug("CTU collect failure ZIP file written at '%s'", zip_file)


def collect_statistics(action, source, clangsa_config, statistics_data):
    """
    Run the statistics collection command and save the
    stdout and stderr to a file.
    """
    cmd, can_collect = statistics.build_stat_coll_cmd(action, clangsa_config,
                                                      source)

    if not can_collect:
        LOG.debug('Can not collect statistical data.')
        return None

    LOG.debug_analyzer(shlex.join(cmd))

    ret_code, analyzer_out, analyzer_err = \
        analyzer_base.SourceAnalyzer.run_proc(cmd)

    LOG.debug_analyzer(analyzer_out)
    LOG.debug_analyzer(analyzer_err)
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
PROGRESS_CHECKED_NUM: Any = None
PROGRESS_ACTIONS: Any = None


def init_worker(checked_num, action_num):
    global PROGRESS_CHECKED_NUM, PROGRESS_ACTIONS
    PROGRESS_CHECKED_NUM = checked_num
    PROGRESS_ACTIONS = action_num


def pre_analyze(params):
    """
    Run the pre-analysis steps of one build action. Returns True if a CTU
    collect step failed for the action.
    """
    action, clangsa_config, skip_handlers, ctu_data, statistics_data, \
        output_path = params

    PROGRESS_CHECKED_NUM.value += 1

    if skip_handlers and skip_handlers.should_skip(action.source):
        return False
    if action.analyzer_type != ClangSA.ANALYZER_NAME:
        return False

    _, source_filename = os.path.split(action.source)

    LOG.info("[%d/%d] %s",
             PROGRESS_CHECKED_NUM.value,
             PROGRESS_ACTIONS.value, source_filename)

    ctu_failures = []
    try:
        if ctu_data:
            LOG.debug("running CTU pre analysis")
            if output_path:
                remove_ctu_collect_zips(action,
                                        os.path.join(output_path, 'failed'))

            ctu_temp_fnmap_folder = ctu_data.get('ctu_temp_fnmap_folder')
            ctu_func_map_cmd = ctu_data.get('ctu_func_map_cmd')

            triple_arch = \
                ctu_triple_arch.get_triple_arch(action, action.source,
                                                clangsa_config)

            # TODO: reorganize the various ctu modes parameters
            # Dump-based analysis requires serialized ASTs.
            if clangsa_config.ctu_on_demand:
                ctu_manager.generate_invocation_list(triple_arch, action,
                                                     action.source,
                                                     clangsa_config)
            else:
                ctu_failures.append(
                    ctu_manager.generate_ast(triple_arch, action,
                                             action.source, clangsa_config))
            # On-demand analysis does not require AST-dumps.
            # We map the function names to corresponding sources of ASTs.
            # In case of On-demand analysis this source is the original source
            # code. In case of AST-dump based analysis these sources are the
            # generated AST-dumps.
            ctu_failures.append(
                ctu_manager.map_functions(triple_arch, action, action.source,
                                          clangsa_config, ctu_func_map_cmd,
                                          ctu_temp_fnmap_folder))

    except Exception as ex:
        LOG.error("Pre-analysis failed for %s: %s", action.source, str(ex))
        traceback.print_exc(file=sys.stdout)
        if ctu_data:
            ctu_failures.append(ctu_manager.collect_failure(
                'exception', [], -1, '', traceback.format_exc()))

    ctu_failures = [f for f in ctu_failures if f]
    if output_path:
        for failure in ctu_failures:
            try:
                save_ctu_collect_failure(action, failure, output_path)
            except Exception as ex:
                LOG.error("Failed to save the CTU collect failure of %s: %s",
                          action.source, str(ex))

    try:
        if statistics_data:
            LOG.debug("running statistics pre analysis")
            collect_statistics(action,
                               action.source,
                               clangsa_config,
                               statistics_data)

    except Exception as ex:
        LOG.debug(str(ex))
        traceback.print_exc(file=sys.stdout)
        raise

    return bool(ctu_failures)


def run_pre_analysis(actions, clangsa_config,
                     jobs, skip_handlers, ctu_data, statistics_data, manager,
                     output_path=None):
    """
    Run multiple pre analysis jobs before the actual analysis.

    If output_path is given, the failures of the CTU collect phase are saved
    into its 'failed' directory.
    """
    LOG.info('Pre-analysis started.')
    if ctu_data:
        LOG.info("Collecting data for ctu analysis.")
    if statistics_data:
        LOG.info("Collecting data for statistical analysis.")

    def signal_handler(signum, _):
        try:
            pool.terminate()
            manager.shutdown()
        finally:
            sys.exit(128 + signum)

    signal.signal(signal.SIGINT, signal_handler)

    processed_var = multiprocess.Value('i', 0)
    actions_num = multiprocess.Value('i', len(actions))

    pool = multiprocess.Pool(jobs,
                             initializer=init_worker,
                             initargs=(processed_var, actions_num))

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
                            clangsa_config,
                            skip_handlers,
                            ctu_data,
                            statistics_data,
                            output_path)
                           for build_action in actions]
        # FIXME: Ensure all shared data structures are wrapped in manager
        #        proxy objects before passing them to other processes via
        #        map_async.
        #        Note that even deep-copying is known to be insufficient.
        result = pool.map_async(pre_analyze, collect_actions)
        pool.close()
    except Exception:
        pool.terminate()
        raise
    finally:
        pool.join()
        # Return whether the call completed without raising an exception.
        if not result.successful():
            # If the remote call raised an exception then that exception will
            # be reraised by get().
            result.get()

    # Postprocessing the pre analysis results.
    if ctu_data:
        ctu_collect_failed = sum(1 for failed in result.get() if failed)
        if ctu_collect_failed:
            LOG.warning("CTU collect phase failed for %d compilation "
                        "command(s).%s", ctu_collect_failed,
                        f" Failure archives are in "
                        f"'{os.path.join(output_path, 'failed')}'."
                        if output_path else "")

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
