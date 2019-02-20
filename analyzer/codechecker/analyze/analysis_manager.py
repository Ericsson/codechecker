# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import glob
import multiprocessing
import os
import shlex
import shutil
import signal
import sys
import traceback
import zipfile

from libcodechecker import util, plist_parser
from libcodechecker.env import get_check_env
from libcodechecker.logger import get_logger
from tu_collector import tu_collector

from . import gcc_toolchain
from .analyzers import analyzer_clangsa
from .analyzers import analyzer_types
from .statistics_collector import SpecialReturnValueCollector

LOG = get_logger('analyzer')


def print_analyzer_statistic_summary(statistics, status, msg=None):
    """
    Print analyzer statistic summary for the given status code with the given
    section heading message.
    """
    has_status = sum((res.get(status, 0) for res in
                      (statistics[i] for i in statistics)))

    if has_status and msg:
        LOG.info(msg)

    for analyzer_type, res in statistics.items():
        successful = res[status]
        if successful:
            LOG.info("  %s: %s", analyzer_type, successful)


def worker_result_handler(results, metadata, output_path, analyzer_binaries):
    """
    Print the analysis summary.
    """

    if metadata is None:
        metadata = {}

    skipped_num = 0
    reanalyzed_num = 0
    statistics = {}

    for res, skipped, reanalyzed, analyzer_type, _, sources in results:
        if skipped:
            skipped_num += 1
        else:
            if reanalyzed:
                reanalyzed_num += 1

            if analyzer_type not in statistics:
                analyzer_bin = analyzer_binaries[analyzer_type]
                analyzer_version = \
                    metadata.get('versions', {}).get(analyzer_bin)

                statistics[analyzer_type] = {
                    "failed": 0,
                    "failed_sources": [],
                    "successful": 0,
                    "version": analyzer_version
                }

            if res == 0:
                statistics[analyzer_type]['successful'] += 1
            else:
                statistics[analyzer_type]['failed'] += 1
                statistics[analyzer_type]['failed_sources'].append(sources)

    LOG.info("----==== Summary ====----")
    print_analyzer_statistic_summary(statistics,
                                     'successful',
                                     'Successfully analyzed')

    print_analyzer_statistic_summary(statistics,
                                     'failed',
                                     'Failed to analyze')

    if reanalyzed_num:
        LOG.info("Reanalyzed compilation commands: %d", reanalyzed_num)
    if skipped_num:
        LOG.info("Skipped compilation commands: %d", skipped_num)

    metadata['skipped'] = skipped_num
    metadata['analyzer_statistics'] = statistics

    # check() created the result .plist files and additional, per-analysis
    # meta information in forms of .plist.source files.
    # We now soak these files into the metadata dict, as they are not needed
    # as loose files on the disk... but synchronizing LARGE dicts between
    # threads would be more error prone.
    source_map = {}
    for f in glob.glob(os.path.join(output_path, "*.source")):
        with open(f, 'r') as sfile:
            source_map[f[:-7]] = sfile.read().strip()
        os.remove(f)

    for f in glob.glob(os.path.join(output_path, 'failed', "*.error")):
        err_file, _ = os.path.splitext(f)
        plist_file = os.path.basename(err_file) + ".plist"
        plist_file = os.path.join(output_path, plist_file)
        metadata['result_source_files'].pop(plist_file, None)

    metadata['result_source_files'].update(source_map)


# Progress reporting.
progress_checked_num = None
progress_actions = None


def init_worker(checked_num, action_num):
    global progress_checked_num, progress_actions
    progress_checked_num = checked_num
    progress_actions = action_num


def save_output(base_file_name, out, err):
    try:
        if out:
            with open(base_file_name + ".stdout.txt", 'w') as outf:
                outf.write(out)

        if err:
            with open(base_file_name + ".stderr.txt", 'w') as outf:
                outf.write(err)
    except IOError as ioerr:
        LOG.debug("Failed to save analyzer output")
        LOG.debug(ioerr)


def save_metadata(result_file, analyzer_result_file, analyzed_source_file):
    """
    Save some extra information next to the plist, .source
    acting as an extra metadata file.
    """
    with open(result_file + ".source", 'w') as orig:
        orig.write(analyzed_source_file.replace(r'\ ', ' ') + "\n")

    if os.path.exists(analyzer_result_file) and \
            not os.path.exists(result_file):
        os.rename(analyzer_result_file, result_file)


def is_ctu_active(source_analyzer):
    """
    Check if CTU analysis is active for Clang Static Analyzer.
    """
    if not isinstance(source_analyzer, analyzer_clangsa.ClangSA):
        return False

    return source_analyzer.is_ctu_available() and \
        source_analyzer.is_ctu_enabled()


def prepare_check(action, analyzer_config_map, output_dir,
                  severity_map, skip_handler, statistics_data,
                  disable_ctu=False):
    """
    Construct the source analyzer build the analysis command
    and result handler for the analysis.
    """
    reanalyzed = False

    # Create a source analyzer.
    source_analyzer = \
        analyzer_types.construct_analyzer(action,
                                          analyzer_config_map)

    if disable_ctu:
        # WARNING! can be called only on ClangSA
        # Needs to be called before construct_analyzer_cmd
        source_analyzer.disable_ctu()

    if action.analyzer_type == analyzer_clangsa.ClangSA.ANALYZER_NAME and \
       statistics_data:
        # WARNING! Statistical checkers are only supported by Clang
        # Static Analyzer right now.
        stats_dir = statistics_data['stats_out_dir']

        # WARNING Because both statistical checkers use the same config
        # directory it is enough to add it only once. This might change later.
        # Configuration arguments should be added before the checkers are
        # enabled.
        stats_cfg = \
            SpecialReturnValueCollector.checker_analyze_cfg(stats_dir)

        source_analyzer.add_checker_config(stats_cfg)

    # Source is the currently analyzed source file
    # there can be more in one buildaction.
    source_analyzer.source_file = action.source

    # The result handler for analysis is an empty result handler
    # which only returns metadata, but can't process the results.
    rh = source_analyzer.construct_result_handler(action,
                                                  output_dir,
                                                  severity_map,
                                                  skip_handler)

    # NOTICE!
    # The currently analyzed source file needs to be set before the
    # analyzer command is constructed.
    # The analyzer output file is based on the currently
    # analyzed source.
    rh.analyzed_source_file = action.source

    if os.path.exists(rh.analyzer_result_file):
        reanalyzed = True

    # Construct the analyzer cmd.
    analyzer_cmd = source_analyzer.construct_analyzer_cmd(rh)

    return source_analyzer, analyzer_cmd, rh, reanalyzed


def handle_success(rh, result_file, result_base, skip_handler,
                   capture_analysis_output, success_dir):
    """
    Result postprocessing is required if the analysis was
    successful (mainly clang tidy output conversion is done).

    Skipping reports for header files is done here too.
    """
    if capture_analysis_output:
        save_output(os.path.join(success_dir, result_base),
                    rh.analyzer_stdout, rh.analyzer_stderr)

    rh.postprocess_result()
    # Generated reports will be handled separately at store.

    save_metadata(result_file, rh.analyzer_result_file,
                  rh.analyzed_source_file)

    if skip_handler:
        # We need to check the plist content because skipping
        # reports in headers can be done only this way.
        plist_parser.skip_report_from_plist(result_file,
                                            skip_handler)


def handle_failure(source_analyzer, rh, zip_file, result_base, actions_map):
    """
    If the analysis fails a debug zip is packed together which contains
    build, analysis information and source files to be able to
    reproduce the failed analysis.
    """
    other_files = set()
    action = rh.buildaction

    try:
        LOG.debug("Fetching other dependent files from analyzer "
                  "output...")
        other_files.update(
            source_analyzer.get_analyzer_mentioned_files(
                rh.analyzer_stdout))

        other_files.update(
            source_analyzer.get_analyzer_mentioned_files(
                rh.analyzer_stderr))
    except Exception as ex:
        LOG.debug("Couldn't generate list of other files "
                  "from analyzer output:")
        LOG.debug(str(ex))

    LOG.debug("Collecting debug data")

    buildactions = [{
        'file': action.source,
        'command': action.original_command,
        'directory': action.directory}]

    for of in other_files:
        mentioned_file = os.path.abspath(os.path.join(action.directory, of))
        key = mentioned_file, action.target
        mentioned_file_action = actions_map.get(key)
        if mentioned_file_action is not None:
            buildactions.append({
                'file': mentioned_file_action.source,
                'command': mentioned_file_action.original_command,
                'directory': mentioned_file_action.directory})
        else:
            LOG.debug("Could not find %s in build actions.", key)

    tu_collector.zip_tu_files(zip_file, buildactions)

    # TODO: What about the dependencies of the other_files?
    tu_collector.add_sources_to_zip(
        zip_file,
        map(lambda path: os.path.join(action.directory, path), other_files))

    with zipfile.ZipFile(zip_file, 'a') as archive:
        LOG.debug("[ZIP] Writing analyzer STDOUT to /stdout")
        archive.writestr("stdout", rh.analyzer_stdout)

        LOG.debug("[ZIP] Writing analyzer STDERR to /stderr")
        archive.writestr("stderr", rh.analyzer_stderr)

        LOG.debug("[ZIP] Writing extra information...")
        archive.writestr("build-action", action.original_command)
        archive.writestr("analyzer-command", ' '.join(rh.analyzer_cmd))
        archive.writestr("return-code", str(rh.analyzer_returncode))

        toolchain = gcc_toolchain.toolchain_in_args(
            shlex.split(action.original_command))
        if toolchain:
            archive.writestr("gcc-toolchain-path", toolchain)

    LOG.debug("ZIP file written at '%s'", zip_file)

    # Remove files that successfully analyzed earlier on.
    plist_file = result_base + ".plist"
    if os.path.exists(plist_file):
        os.remove(plist_file)


def check(check_data):
    """
    Invoke clang with an action which called by processes.
    Different analyzer object belongs to for each build action.

    skiplist handler is None if no skip file was configured.
    """
    actions_map, action, context, analyzer_config_map, \
        output_dir, skip_handler, quiet_output_on_stdout, \
        capture_analysis_output, analysis_timeout, \
        analyzer_environment, ctu_reanalyze_on_failure, \
        output_dirs, statistics_data = check_data

    failed_dir = output_dirs["failed"]
    success_dir = output_dirs["success"]

    try:
        # If one analysis fails the check fails.
        return_codes = 0
        reanalyzed = False

        result_file = ''

        source_analyzer, analyzer_cmd, rh, reanalyzed = \
            prepare_check(action, analyzer_config_map,
                          output_dir, context.severity_map,
                          skip_handler, statistics_data)

        # The analyzer invocation calls __create_timeout as a callback
        # when the analyzer starts. This callback creates the timeout
        # watcher over the analyzer process, which in turn returns a
        # function, that can later be used to check if the analyzer quit
        # because we killed it due to a timeout.
        #
        # We need to capture the "function pointer" returned by
        # setup_process_timeout as reference, so that we may call it
        # later. To work around scoping issues, we use a list here so the
        # "function pointer" is captured by reference.
        timeout_cleanup = [lambda: False]

        if analysis_timeout and analysis_timeout > 0:
            def __create_timeout(analyzer_process):
                """
                Once the analyzer process is started, this method is
                called. Set up a timeout for the analysis.
                """
                timeout_cleanup[0] = util.setup_process_timeout(
                    analyzer_process, analysis_timeout)
        else:
            def __create_timeout(analyzer_process):
                # If no timeout is given by the client, this callback
                # shouldn't do anything.
                pass

        # Fills up the result handler with the analyzer information.
        source_analyzer.analyze(analyzer_cmd, rh, analyzer_environment,
                                __create_timeout)

        # If execution reaches this line, the analyzer process has quit.
        if timeout_cleanup[0]():
            LOG.warning("Analyzer ran too long, exceeding time limit "
                        "of %d seconds.", analysis_timeout)
            LOG.warning("Considering this analysis as failed...")
            rh.analyzer_returncode = -1
            rh.analyzer_stderr = (">>> CodeChecker: Analysis timed out "
                                  "after {0} seconds. <<<\n{1}") \
                .format(analysis_timeout, rh.analyzer_stderr)

        # If source file contains escaped spaces ("\ " tokens), then
        # clangSA writes the plist file with removing this escape
        # sequence, whereas clang-tidy does not. We rewrite the file
        # names to contain no escape sequences for every analyzer.
        result_file = rh.analyzer_result_file.replace(r'\ ', ' ')
        result_base = os.path.basename(result_file)

        ctu_active = is_ctu_active(source_analyzer)

        ctu_suffix = '_CTU'
        zip_suffix = ctu_suffix if ctu_active else ''

        failure_type = "_unknown"
        if rh.analyzer_returncode == 1:
            failure_type = "_compile_error"
        elif rh.analyzer_returncode == 254:
            failure_type = "_crash"

        zip_file = result_base + zip_suffix + failure_type + '.zip'
        zip_file = os.path.join(failed_dir, zip_file)

        ctu_zip_file = result_base + ctu_suffix + failure_type + '.zip'
        ctu_zip_file = os.path.join(failed_dir, ctu_zip_file)

        return_codes = rh.analyzer_returncode

        source_file_name = os.path.basename(action.source)

        if rh.analyzer_returncode == 0:

            # Remove the previously generated error file.
            if os.path.exists(zip_file):
                os.remove(zip_file)

            # Remove the previously generated CTU error file.
            if os.path.exists(ctu_zip_file):
                os.remove(ctu_zip_file)

            handle_success(rh, result_file, result_base,
                           skip_handler, capture_analysis_output,
                           success_dir)
            LOG.info("[%d/%d] %s analyzed %s successfully.",
                     progress_checked_num.value, progress_actions.value,
                     action.analyzer_type, source_file_name)

            if skip_handler:
                # We need to check the plist content because skipping
                # reports in headers can be done only this way.
                plist_parser.skip_report_from_plist(result_file,
                                                    skip_handler)

        else:
            LOG.error("Analyzing %s with %s %s failed!",
                      source_file_name,
                      action.analyzer_type,
                      "CTU" if ctu_active else "")

            if not quiet_output_on_stdout:
                LOG.error("\n%s", rh.analyzer_stdout)
                LOG.error("\n%s", rh.analyzer_stderr)

            handle_failure(source_analyzer, rh, zip_file, result_base,
                           actions_map)

            if ctu_active and ctu_reanalyze_on_failure:
                LOG.error("Try to reanalyze without CTU")
                # Try to reanalyze with CTU disabled.
                source_analyzer, analyzer_cmd, rh, reanalyzed = \
                    prepare_check(action,
                                  analyzer_config_map,
                                  output_dir,
                                  context.severity_map,
                                  skip_handler,
                                  statistics_data,
                                  True)

                # Fills up the result handler with
                # the analyzer information.
                source_analyzer.analyze(analyzer_cmd,
                                        rh,
                                        analyzer_environment)

                return_codes = rh.analyzer_returncode
                if rh.analyzer_returncode == 0:
                    handle_success(rh, result_file, result_base,
                                   skip_handler, capture_analysis_output,
                                   success_dir)

                    LOG.info("[%d/%d] %s analyzed %s without"
                             " CTU successfully.",
                             progress_checked_num.value,
                             progress_actions.value,
                             action.analyzer_type,
                             source_file_name)

                else:

                    LOG.error("Analyzing '%s' with %s without CTU failed.",
                              source_file_name, action.analyzer_type)

                    zip_file = result_base + '.zip'
                    zip_file = os.path.join(failed_dir, zip_file)
                    handle_failure(source_analyzer, rh, zip_file,
                                   result_base, actions_map)

        if not quiet_output_on_stdout:
            if rh.analyzer_returncode:
                LOG.error('\n%s', rh.analyzer_stdout)
                LOG.error('\n%s', rh.analyzer_stderr)
            else:
                LOG.debug_analyzer('\n%s', rh.analyzer_stdout)
                LOG.debug_analyzer('\n%s', rh.analyzer_stderr)

        progress_checked_num.value += 1

        return return_codes, False, reanalyzed, action.analyzer_type, \
            result_file, action.source

    except Exception as e:
        LOG.debug_analyzer(str(e))
        traceback.print_exc(file=sys.stdout)
        return 1, False, reanalyzed, action.analyzer_type, None, \
            action.source


def skip_cpp(compile_actions, skip_handler):
    """If there is no skiplist handler there was no skip list file in
       the command line.
       C++ file skipping is handled here.
    """

    if not skip_handler:
        return compile_actions, []

    analyze = []
    skip = []
    for compile_action in compile_actions:

        if skip_handler and skip_handler.should_skip(compile_action.source):
            skip.append(compile_action)
        else:
            analyze.append(compile_action)

    return analyze, skip


def start_workers(actions_map, actions, context, analyzer_config_map,
                  jobs, output_path, skip_handler, metadata,
                  quiet_analyze, capture_analysis_output, timeout,
                  ctu_reanalyze_on_failure, statistics_data, manager):
    """
    Start the workers in the process pool.
    For every build action there is worker which makes the analysis.
    """

    # Handle SIGINT to stop this script running.
    def signal_handler(*arg, **kwarg):
        try:
            pool.terminate()
            manager.shutdown()
        finally:
            sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    # Start checking parallel.
    checked_var = multiprocessing.Value('i', 1)
    actions_num = multiprocessing.Value('i', len(actions))
    pool = multiprocessing.Pool(jobs,
                                initializer=init_worker,
                                initargs=(checked_var,
                                          actions_num))

    failed_dir = os.path.join(output_path, "failed")
    # If the analysis has failed, we help debugging.
    if not os.path.exists(failed_dir):
        os.makedirs(failed_dir)

    success_dir = os.path.join(output_path, "success")

    # Analysis was successful processing results.
    if not os.path.exists(success_dir):
        os.makedirs(success_dir)

    output_dirs = {'success': success_dir,
                   'failed': failed_dir}

    # Construct analyzer env.
    analyzer_environment = get_check_env(context.path_env_extra,
                                         context.ld_lib_path_extra)

    actions, skipped_actions = skip_cpp(actions, skip_handler)

    analyzed_actions = [(actions_map,
                         build_action,
                         context,
                         analyzer_config_map,
                         output_path,
                         skip_handler,
                         quiet_analyze,
                         capture_analysis_output,
                         timeout,
                         analyzer_environment,
                         ctu_reanalyze_on_failure,
                         output_dirs,
                         statistics_data)
                        for build_action in actions]

    if analyzed_actions:
        try:

            # Workaround, equivalent of map.
            # The main script does not get signal
            # while map or map_async function is running.
            # It is a python bug, this does not happen if a timeout is
            # specified, then receive the interrupt immediately.
            pool.map_async(check,
                           analyzed_actions,
                           1,
                           callback=lambda results: worker_result_handler(
                               results, metadata, output_path,
                               context.analyzer_binaries)
                           ).get(float('inf'))

            pool.close()
        except Exception:
            pool.terminate()
            raise
        finally:
            pool.join()
    else:
        LOG.info("----==== Summary ====----")

    for skp in skipped_actions:
        LOG.debug_analyzer("%s is skipped", skp.source)

    LOG.info("Total analyzed compilation commands: %d", len(analyzed_actions))

    LOG.info("----=================----")
    if not os.listdir(success_dir):
        shutil.rmtree(success_dir)

    if not os.listdir(failed_dir):
        shutil.rmtree(failed_dir)
