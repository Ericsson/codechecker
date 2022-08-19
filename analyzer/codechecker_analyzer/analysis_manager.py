# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
"""


import glob
import multiprocessing
import os
import shlex
import shutil
import signal
import sys
import time
import traceback
import zipfile

from threading import Timer

import psutil

from codechecker_analyzer import env
from codechecker_common.logger import get_logger

from codechecker_statistics_collector.collectors.special_return_value import \
    SpecialReturnValueCollector

from . import gcc_toolchain

from .analyzers import analyzer_types
from .analyzers.config_handler import CheckerState
from .analyzers.clangsa.analyzer import ClangSA

LOG = get_logger('analyzer')


def print_analyzer_statistic_summary(metadata_analyzers, status, msg=None):
    """
    Print analyzer statistic summary for the given status code with the given
    section heading message.
    """
    has_status = False
    for _, analyzer in metadata_analyzers.items():
        if analyzer.get('analyzer_statistics', {}).get(status):
            has_status = True
            break

    if has_status and msg:
        LOG.info(msg)

    for analyzer_type, analyzer in metadata_analyzers.items():
        res = analyzer.get('analyzer_statistics', {}).get(status)
        if res:
            LOG.info("  %s: %s", analyzer_type, res)


def worker_result_handler(results, metadata_tool, output_path,
                          analyzer_binaries):
    """ Print the analysis summary. """
    skipped_num = 0
    reanalyzed_num = 0
    metadata_analyzers = metadata_tool['analyzers']
    for res, skipped, reanalyzed, analyzer_type, _, sources in results:
        statistics = metadata_analyzers[analyzer_type]['analyzer_statistics']
        if skipped:
            skipped_num += 1
        else:
            if reanalyzed:
                reanalyzed_num += 1

            if res == 0:
                statistics['successful'] += 1
                statistics['successful_sources'].append(sources)
            else:
                statistics['failed'] += 1
                statistics['failed_sources'].append(sources)

    LOG.info("----==== Summary ====----")
    print_analyzer_statistic_summary(metadata_analyzers,
                                     'successful',
                                     'Successfully analyzed')

    print_analyzer_statistic_summary(metadata_analyzers,
                                     'failed',
                                     'Failed to analyze')

    if reanalyzed_num:
        LOG.info("Reanalyzed compilation commands: %d", reanalyzed_num)
    if skipped_num:
        LOG.info("Skipped compilation commands: %d", skipped_num)

    metadata_tool['skipped'] = skipped_num

    # check() created the result .plist files and additional, per-analysis
    # meta information in forms of .plist.source files.
    # We now soak these files into the metadata dict, as they are not needed
    # as loose files on the disk... but synchronizing LARGE dicts between
    # threads would be more error prone.
    source_map = {}
    for f in glob.glob(os.path.join(output_path, "*.source")):
        with open(f, 'r', encoding="utf-8", errors="ignore") as sfile:
            source_map[f[:-7]] = sfile.read().strip()
        os.remove(f)

    for f in glob.glob(os.path.join(output_path, 'failed', "*.error")):
        err_file, _ = os.path.splitext(f)
        plist_file = os.path.basename(err_file) + ".plist"
        plist_file = os.path.join(output_path, plist_file)
        metadata_tool['result_source_files'].pop(plist_file, None)

    metadata_tool['result_source_files'].update(source_map)


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
            with open(base_file_name + ".stdout.txt", 'w',
                      encoding="utf-8", errors="ignore") as outf:
                outf.write(out)

        if err:
            with open(base_file_name + ".stderr.txt", 'w',
                      encoding="utf-8", errors="ignore") as outf:
                outf.write(err)
    except IOError as ioerr:
        LOG.debug("Failed to save analyzer output")
        LOG.debug(ioerr)


def save_metadata(result_file, analyzer_result_file, analyzed_source_file):
    """
    Save some extra information next to the plist, .source
    acting as an extra metadata file.
    """
    with open(result_file + ".source", 'w',
              encoding="utf-8", errors="ignore") as orig:
        orig.write(analyzed_source_file.replace(r'\ ', ' ') + "\n")

    if os.path.exists(analyzer_result_file) and \
            not os.path.exists(result_file):
        os.rename(analyzer_result_file, result_file)


def is_ctu_active(source_analyzer):
    """
    Check if CTU analysis is active for Clang Static Analyzer.
    """
    if not isinstance(source_analyzer, ClangSA):
        return False

    return source_analyzer.is_ctu_available() and \
        source_analyzer.is_ctu_enabled()


def prepare_check(action, analyzer_config, output_dir, checker_labels,
                  skip_handlers, statistics_data, disable_ctu=False):
    """ Construct the source analyzer and result handler. """
    # Create a source analyzer.
    source_analyzer = \
        analyzer_types.construct_analyzer(action,
                                          analyzer_config)

    if disable_ctu:
        # WARNING! can be called only on ClangSA
        # Needs to be called before construct_analyzer_cmd
        source_analyzer.disable_ctu()

    if action.analyzer_type == ClangSA.ANALYZER_NAME and \
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

        if os.path.exists(SpecialReturnValueCollector.stats_file(stats_dir)):
            source_analyzer.add_checker_config(stats_cfg)
        else:
            LOG.debug('No checker statistics file was found for %s',
                      SpecialReturnValueCollector.checker_analyze)

    # Source is the currently analyzed source file
    # there can be more in one buildaction.
    source_analyzer.source_file = action.source

    # The result handler for analysis is an empty result handler
    # which only returns metadata, but can't process the results.
    rh = source_analyzer.construct_result_handler(action,
                                                  output_dir,
                                                  checker_labels,
                                                  skip_handlers)

    # NOTICE!
    # The currently analyzed source file needs to be set before the
    # analyzer command is constructed.
    # The analyzer output file is based on the currently
    # analyzed source.
    rh.analyzed_source_file = action.source
    return source_analyzer, rh


def handle_success(rh, result_file, result_base, skip_handlers,
                   capture_analysis_output, success_dir):
    """
    Result postprocessing is required if the analysis was
    successful (mainly clang tidy output conversion is done).

    Skipping reports for header files is done here too.
    """
    if capture_analysis_output:
        save_output(os.path.join(success_dir, result_base),
                    rh.analyzer_stdout, rh.analyzer_stderr)

    rh.postprocess_result(skip_handlers)

    # Generated reports will be handled separately at store.

    save_metadata(result_file, rh.analyzer_result_file,
                  rh.analyzed_source_file)


def handle_reproducer(source_analyzer, rh, zip_file, actions_map):
    """
    If the analysis fails a debug zip is packed together which contains
    build, analysis information and source files to be able to
    reproduce the failed analysis.
    """
    other_files = set()
    action = rh.buildaction

    try:
        LOG.debug("Fetching other dependent files from analyzer output...")
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

    from tu_collector import tu_collector

    tu_collector.zip_tu_files(zip_file, buildactions)

    # TODO: What about the dependencies of the other_files?
    tu_collector.add_sources_to_zip(
        zip_file,
        [os.path.join(action.directory, path) for path in other_files])

    with zipfile.ZipFile(zip_file, 'a') as archive:
        LOG.debug("[ZIP] Writing analyzer STDOUT to /stdout")
        archive.writestr("stdout", rh.analyzer_stdout)

        LOG.debug("[ZIP] Writing analyzer STDERR to /stderr")
        archive.writestr("stderr", rh.analyzer_stderr)

        LOG.debug("[ZIP] Writing extra information...")
        archive.writestr("build-action", action.original_command)
        archive.writestr(
            "analyzer-command",
            ' '.join([shlex.quote(x) for x in rh.analyzer_cmd]),
            )
        archive.writestr("return-code", str(rh.analyzer_returncode))

        toolchain = gcc_toolchain.toolchain_in_args(
            shlex.split(action.original_command))
        if toolchain:
            archive.writestr("gcc-toolchain-path", toolchain)

        compiler_info_file = os.path.join(rh.workspace, 'compiler_info.json')
        if os.path.exists(compiler_info_file):
            archive.write(compiler_info_file, "compiler_info.json")

    LOG.debug("ZIP file written at '%s'", zip_file)


def handle_failure(
    source_analyzer, rh, zip_file, result_base, actions_map, skip_handlers
):
    """
    If the analysis fails a debug zip is packed together which contains
    build, analysis information and source files to be able to
    reproduce the failed analysis.
    """
    handle_reproducer(source_analyzer, rh, zip_file, actions_map)

    # In case of compiler errors the error message still needs to be collected
    # from the standard output by this postprocess phase so we can present them
    # as CodeChecker reports.
    checks = source_analyzer.config_handler.checks()
    state = checks.get('clang-diagnostic-error', (CheckerState.default, ''))[0]
    if state != CheckerState.disabled:
        rh.postprocess_result(skip_handlers)

    # Remove files that successfully analyzed earlier on.
    plist_file = result_base + ".plist"
    if os.path.exists(plist_file):
        os.remove(plist_file)


def kill_process_tree(parent_pid, recursive=False):
    """Stop the process tree try it gracefully first.

    Try to stop the parent and child processes gracefuly
    first if they do not stop in time send a kill signal
    to every member of the process tree.

    There is a similar function in the web part please
    consider to update that in case of changing this.
    """
    proc = psutil.Process(parent_pid)
    children = proc.children(recursive)

    # Send a SIGTERM (Ctrl-C) to the main process
    proc.terminate()

    # If children processes don't stop gracefully in time,
    # slaughter them by force.
    _, still_alive = psutil.wait_procs(children, timeout=5)
    for p in still_alive:
        p.kill()

    # Wait until this process is running.
    n = 0
    timeout = 10
    while proc.is_running():
        if n > timeout:
            LOG.warning("Waiting for process %s to stop has been timed out"
                        "(timeout = %s)! Process is still running!",
                        parent_pid, timeout)
            break

        time.sleep(1)
        n += 1


def setup_process_timeout(proc, timeout,
                          failure_callback=None):
    """
    Setup a timeout on a process. After `timeout` seconds, the process is
    killed by `signal_at_timeout` signal.

    :param proc: The subprocess.Process object representing the process to
      attach the watcher to.
    :param timeout: The timeout the process is allowed to run for, in seconds.
      This timeout is counted down some moments after calling
      setup_process_timeout(), and due to OS scheduling, might not be exact.
    :param failure_callback: An optional function which is called when the
      process is killed by the timeout. This is called with no arguments
      passed.

    :return: A function is returned which should be called when the client code
      (usually via subprocess.Process.wait() or
      subprocess.Process.communicate())) figures out that the called process
      has terminated. (See below for what this called function returns.)
    """

    # The watch dict encapsulated the captured variables for the timeout watch.
    watch = {'pid': proc.pid,
             'timer': None,  # Will be created later.
             'counting': False,
             'killed': False}

    def __kill():
        """
        Helper function to execute the killing of a hung process.
        """
        LOG.debug("Process %s has ran for too long, killing it!",
                  watch['pid'])
        watch['counting'] = False
        watch['killed'] = True
        kill_process_tree(watch['pid'], True)

        if failure_callback:
            failure_callback()

    timer = Timer(timeout, __kill)
    watch['timer'] = timer

    LOG.debug("Setup timeout of %s for PID %s", proc.pid, timeout)
    timer.start()
    watch['counting'] = True

    def __cleanup_timeout():
        """
        Stops the timer associated with the timeout watch if the process
        finished within the grace period.

        Due to race conditions and the possibility of the OS, or another
        process also using signals to kill the watched process in particular,
        it is possible that checking subprocess.Process.returncode on the
        watched process is not enough to see if the timeout watched killed it,
        or something else.

        (Note: returncode is -N where N is the signal's value, but only on Unix
        systems!)

        It is safe to call this function multiple times to check for the result
        of the watching.

        :return: Whether or not the process was killed by the watcher. If this
          is False, the process could have finished gracefully, or could have
          been destroyed by other means.
        """
        if watch['counting'] and not watch['killed'] and watch['timer']:
            watch['timer'].cancel()
            watch['timer'] = None
            watch['counting'] = False

        return watch['killed']

    return __cleanup_timeout


def collect_ctu_involved_files(result_handler, source_analyzer, output_dir):
    """
    This function collects the list of source files involved by CTU analysis.
    The list of files are written to output_dir.
    """
    if source_analyzer.ANALYZER_NAME != ClangSA.ANALYZER_NAME:
        return

    involved_files = set()

    involved_files.update(source_analyzer.get_analyzer_mentioned_files(
        result_handler.analyzer_stdout))
    involved_files.update(source_analyzer.get_analyzer_mentioned_files(
        result_handler.analyzer_stderr))

    out = os.path.join(output_dir, result_handler.analyzer_action_str)

    if involved_files:
        with open(out, 'w', encoding='utf-8', errors='ignore') as f:
            f.write('\n'.join(involved_files))
    elif os.path.exists(out):
        os.remove(out)


def check(check_data):
    """
    Invoke clang with an action which called by processes.
    Different analyzer object belongs to for each build action.

    skiplist handler is None if no skip file was configured.
    """
    actions_map, action, context, analyzer_config, \
        output_dir, skip_handlers, quiet_output_on_stdout, \
        capture_analysis_output, generate_reproducer, analysis_timeout, \
        analyzer_environment, ctu_reanalyze_on_failure, \
        output_dirs, statistics_data = check_data

    failed_dir = output_dirs["failed"]
    success_dir = output_dirs["success"]
    reproducer_dir = output_dirs["reproducer"]

    try:
        # If one analysis fails the check fails.
        return_codes = 0
        reanalyzed = False

        result_file = ''

        if analyzer_config is None:
            raise Exception("Analyzer configuration is missing.")

        source_analyzer, rh = prepare_check(action, analyzer_config,
                                            output_dir, context.checker_labels,
                                            skip_handlers, statistics_data)

        reanalyzed = os.path.exists(rh.analyzer_result_file)

        # Construct the analyzer cmd.
        analyzer_cmd = source_analyzer.construct_analyzer_cmd(rh)

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
                timeout_cleanup[0] = setup_process_timeout(
                    analyzer_process, analysis_timeout)
        else:
            def __create_timeout(analyzer_process):
                # If no timeout is given by the client, this callback
                # shouldn't do anything.
                pass

        result_file_exists = os.path.exists(rh.analyzer_result_file)

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

        source_analyzer.post_analyze(rh)

        # If source file contains escaped spaces ("\ " tokens), then
        # clangSA writes the plist file with removing this escape
        # sequence, whereas clang-tidy does not. We rewrite the file
        # names to contain no escape sequences for every analyzer.
        result_file = rh.analyzer_result_file.replace(r'\ ', ' ')
        result_base = os.path.basename(result_file)

        ctu_active = is_ctu_active(source_analyzer)

        zip_suffix = '_CTU' if ctu_active else ''

        failure_type = "_unknown"
        if rh.analyzer_returncode == 1:
            failure_type = "_compile_error"
        elif rh.analyzer_returncode == 254:
            failure_type = "_crash"
        elif rh.analyzer_returncode == 0:
            failure_type = ""

        zip_file = result_base + zip_suffix + failure_type + '.zip'
        failed_zip_file = os.path.join(failed_dir, zip_file)
        reproducer_zip_file = os.path.join(reproducer_dir, zip_file)

        return_codes = rh.analyzer_returncode

        source_file_name = os.path.basename(action.source)

        # Remove the previously generated .zip files.
        if os.path.exists(failed_zip_file):
            os.remove(failed_zip_file)
        if os.path.exists(reproducer_zip_file):
            os.remove(reproducer_zip_file)

        def handle_analysis_result(success, zip_file=zip_file):
            """
            Extra actions after executing the analysis. In case of success the
            clang-tidy output is transformed to reports. In case of failure the
            necessary files are collected for debugging. These .zip files can
            also be generated by --generate-reproducer flag.
            """
            if generate_reproducer:
                handle_reproducer(source_analyzer, rh,
                                  os.path.join(reproducer_dir, zip_file),
                                  actions_map)

            if success:
                handle_success(rh, result_file, result_base,
                               skip_handlers, capture_analysis_output,
                               success_dir)
            elif not generate_reproducer:
                handle_failure(source_analyzer, rh,
                               os.path.join(failed_dir, zip_file),
                               result_base, actions_map, skip_handlers)

        if rh.analyzer_returncode == 0:
            handle_analysis_result(success=True)
            LOG.info("[%d/%d] %s analyzed %s successfully.",
                     progress_checked_num.value, progress_actions.value,
                     action.analyzer_type, source_file_name)

            if result_file_exists:
                LOG.warning("Previous analysis results in '%s' has been "
                            "overwritten.", rh.analyzer_result_file)
        else:
            LOG.error("Analyzing %s with %s %s failed!",
                      source_file_name,
                      action.analyzer_type,
                      "CTU" if ctu_active else "")

            if not quiet_output_on_stdout:
                LOG.error("\n%s", rh.analyzer_stdout)
                LOG.error("\n%s", rh.analyzer_stderr)

            handle_analysis_result(success=False)

            if ctu_active and ctu_reanalyze_on_failure:
                LOG.error("Try to reanalyze without CTU")
                # Try to reanalyze with CTU disabled.
                source_analyzer, rh = \
                    prepare_check(action, analyzer_config,
                                  output_dir, context.checker_labels,
                                  skip_handlers, statistics_data,
                                  True)
                reanalyzed = os.path.exists(rh.analyzer_result_file)

                # Construct the analyzer cmd.
                analyzer_cmd = source_analyzer.construct_analyzer_cmd(rh)

                # Fills up the result handler with
                # the analyzer information.
                source_analyzer.analyze(analyzer_cmd,
                                        rh,
                                        analyzer_environment)

                return_codes = rh.analyzer_returncode
                if rh.analyzer_returncode == 0:
                    handle_analysis_result(success=True)

                    LOG.info("[%d/%d] %s analyzed %s without"
                             " CTU successfully.",
                             progress_checked_num.value,
                             progress_actions.value,
                             action.analyzer_type,
                             source_file_name)

                    if result_file_exists:
                        LOG.warning("Previous analysis results in '%s' has "
                                    "been overwritten.",
                                    rh.analyzer_result_file)

                else:
                    LOG.error("Analyzing '%s' with %s without CTU failed.",
                              source_file_name, action.analyzer_type)

                    handle_analysis_result(success=False,
                                           zip_file=result_base + '.zip')

        collect_ctu_involved_files(rh, source_analyzer,
                                   output_dirs['ctu_connections'])

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


def skip_cpp(compile_actions, skip_handlers):
    """If there is no skiplist handler there was no skip list file in
       the command line.
       C++ file skipping is handled here.
    """

    if not skip_handlers:
        return compile_actions, []

    analyze = []
    skip = []
    for compile_action in compile_actions:

        if skip_handlers and skip_handlers.should_skip(compile_action.source):
            skip.append(compile_action)
        else:
            analyze.append(compile_action)

    return analyze, skip


def start_workers(actions_map, actions, context, analyzer_config_map,
                  jobs, output_path, skip_handlers, metadata_tool,
                  quiet_analyze, capture_analysis_output, generate_reproducer,
                  timeout, ctu_reanalyze_on_failure, statistics_data, manager,
                  compile_cmd_count):
    """
    Start the workers in the process pool.
    For every build action there is worker which makes the analysis.
    """

    # Handle SIGINT to stop this script running.
    def signal_handler(signum, frame):
        try:
            pool.terminate()
            manager.shutdown()
        finally:
            sys.exit(128 + signum)

    signal.signal(signal.SIGINT, signal_handler)
    actions, skipped_actions = skip_cpp(actions, skip_handlers)
    # Start checking parallel.
    checked_var = multiprocessing.Value('i', 1)
    actions_num = multiprocessing.Value('i', len(actions))
    pool = multiprocessing.Pool(jobs,
                                initializer=init_worker,
                                initargs=(checked_var,
                                          actions_num))

    # If the analysis has failed, we help debugging.
    failed_dir = os.path.join(output_path, "failed")
    if not os.path.exists(failed_dir):
        os.makedirs(failed_dir)

    # Analysis was successful processing results.
    success_dir = os.path.join(output_path, "success")
    if not os.path.exists(success_dir):
        os.makedirs(success_dir)

    # Similar to failed dir, but generated both in case of success and failure.
    reproducer_dir = os.path.join(output_path, "reproducer")
    if not os.path.exists(reproducer_dir) and generate_reproducer:
        os.makedirs(reproducer_dir)

    # Cppcheck raw output directory.
    cppcheck_dir = os.path.join(output_path, "cppcheck")
    if not os.path.exists(cppcheck_dir):
        os.makedirs(cppcheck_dir)

    # Collect what other TUs were involved during CTU analysis.
    ctu_connections_dir = os.path.join(output_path, "ctu_connections")
    if not os.path.exists(ctu_connections_dir):
        os.makedirs(ctu_connections_dir)

    output_dirs = {'success': success_dir,
                   'failed': failed_dir,
                   'reproducer': reproducer_dir,
                   'ctu_connections': ctu_connections_dir}

    # Construct analyzer env.
    analyzer_environment = env.extend(context.path_env_extra,
                                      context.ld_lib_path_extra)

    analyzed_actions = [(actions_map,
                         build_action,
                         context,
                         analyzer_config_map.get(build_action.analyzer_type),
                         output_path,
                         skip_handlers,
                         quiet_analyze,
                         capture_analysis_output,
                         generate_reproducer,
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

            # FIXME: Ensure all shared data structures are wrapped in manager
            #        proxy objects before passing them to other processes via
            #        map_async.
            #        Note that even deep-copying is known to be insufficient.
            timeout = 3155760 if sys.platform == 'win32' else 31557600
            pool.map_async(check,
                           analyzed_actions,
                           1,
                           callback=lambda results: worker_result_handler(
                               results, metadata_tool, output_path,
                               context.analyzer_binaries)
                           ).get(timeout)

            pool.close()
        except Exception:
            pool.terminate()
            raise
        finally:
            pool.join()
    else:
        pool.close()
        pool.join()
        LOG.info("----==== Summary ====----")

    for skp in skipped_actions:
        LOG.debug_analyzer("%s is skipped", skp.source)

    LOG.info("Total analyzed compilation commands: %d",
             compile_cmd_count.analyze)
    # Some compile commands are skipped during log processing, if nothing
    # is skipped there for pre-analysis step, files will be skipped only
    # during analysis.
    if skipped_actions or compile_cmd_count.skipped:
        LOG.info("Skipped compilation commands: %d",
                 compile_cmd_count.skipped + len(skipped_actions))

    LOG.info("----=================----")
    if not os.listdir(success_dir):
        shutil.rmtree(success_dir)

    if not os.listdir(failed_dir):
        shutil.rmtree(failed_dir)
