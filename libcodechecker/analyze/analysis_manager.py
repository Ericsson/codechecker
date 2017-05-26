# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
"""

from collections import defaultdict
import multiprocessing
import os
import signal
import sys
import traceback

from libcodechecker.analyze import analyzer_env
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('ANALYSIS MANAGER')


def worker_result_handler(results, metadata, output_path):
    """
    Print the analysis summary.
    """

    if metadata is None:
        metadata = {}

    successful_analysis = defaultdict(int)
    failed_analysis = defaultdict(int)
    skipped_num = 0

    for res, skipped, analyzer_type in results:
        if skipped:
            skipped_num += 1
        else:
            if res == 0:
                successful_analysis[analyzer_type] += 1
            else:
                failed_analysis[analyzer_type] += 1

    LOG.info("----==== Summary ====----")
    LOG.info("Total compilation commands: " + str(len(results)))
    if successful_analysis:
        LOG.info("Successfully analyzed")
        for analyzer_type, res in successful_analysis.items():
            LOG.info('  ' + analyzer_type + ': ' + str(res))

    if failed_analysis:
        LOG.info("Failed to analyze")
        for analyzer_type, res in failed_analysis.items():
            LOG.info('  ' + analyzer_type + ': ' + str(res))

    if skipped_num:
        LOG.info("Skipped compilation commands: " + str(skipped_num))
    LOG.info("----=================----")

    metadata['successful'] = successful_analysis
    metadata['failed'] = failed_analysis
    metadata['skipped'] = skipped_num

    # check() created the result .plist files and additional, per-analysis
    # meta information in forms of .plist.source files.
    # We now soak these files into the metadata dict, as they are not needed
    # as loose files on the disk... but synchronizing LARGE dicts between
    # threads would be more error prone.
    source_map = {}
    _, _, files = next(os.walk(output_path), ([], [], []))
    for f in files:
        if not f.endswith(".source"):
            continue

        abspath = os.path.join(output_path, f)
        f = f.replace(".source", '')
        with open(abspath, 'r') as sfile:
            source_map[f] = sfile.read().strip()

        os.remove(abspath)

    metadata['result_source_files'] = source_map


# Progress reporting.
progress_checked_num = None
progress_actions = None


def init_worker(checked_num, action_num):
    global progress_checked_num, progress_actions
    progress_checked_num = checked_num
    progress_actions = action_num


def check(check_data):
    """
    Invoke clang with an action which called by processes.
    Different analyzer object belongs to for each build action.

    skiplist handler is None if no skip file was configured.
    """

    action, context, analyzer_config_map, output_dir, skip_handler = check_data

    skipped = False
    try:
        # If one analysis fails the check fails.
        return_codes = 0
        skipped = False
        for source in action.sources:

            # If there is no skiplist handler there was no skip list file
            # in the command line.
            # C++ file skipping is handled here.
            _, source_file_name = os.path.split(source)

            if skip_handler and skip_handler.should_skip(source):
                LOG.debug_analyzer(source_file_name + ' is skipped')
                skipped = True
                continue

            # Construct analyzer env.
            analyzer_environment = analyzer_env.get_check_env(
                context.path_env_extra,
                context.ld_lib_path_extra)

            # Create a source analyzer.
            source_analyzer = \
                analyzer_types.construct_analyzer(action,
                                                  analyzer_config_map)

            # Source is the currently analyzed source file
            # there can be more in one buildaction.
            source_analyzer.source_file = source

            # The result handler for analysis is an empty result handler
            # which only returns metadata, but can't process the results.
            rh = analyzer_types.construct_analyze_handler(action,
                                                          output_dir,
                                                          context.severity_map,
                                                          skip_handler)

            # Fills up the result handler with the analyzer information.
            source_analyzer.analyze(rh, analyzer_environment)

            if rh.analyzer_returncode == 0:
                # Analysis was successful processing results.
                if rh.analyzer_stdout != '':
                    LOG.debug_analyzer('\n' + rh.analyzer_stdout)
                if rh.analyzer_stderr != '':
                    LOG.debug_analyzer('\n' + rh.analyzer_stderr)
                rh.postprocess_result()
                rh.handle_results()

                # Save some extra information next to the plist, .source
                # acting as an extra metadata file.
                with open(rh.analyzer_result_file + ".source", 'w') as orig:
                    orig.write(rh.analyzed_source_file + "\n")

                LOG.info("[%d/%d] %s analyzed %s successfully." %
                         (progress_checked_num.value, progress_actions.value,
                          action.analyzer_type, source_file_name))
            else:
                # Analysis failed.
                LOG.error('Analyzing ' + source_file_name + ' with ' +
                          action.analyzer_type + ' failed.')
                if rh.analyzer_stdout != '':
                    LOG.error(rh.analyzer_stdout)
                if rh.analyzer_stderr != '':
                    LOG.error(rh.analyzer_stderr)
                return_codes = rh.analyzer_returncode

        progress_checked_num.value += 1

        return return_codes, skipped, action.analyzer_type

    except Exception as e:
        LOG.debug_analyzer(str(e))
        traceback.print_exc(file=sys.stdout)
        return 1, skipped, action.analyzer_type


def start_workers(actions, context, analyzer_config_map,
                  jobs, output_path, skip_handler, metadata):
    """
    Start the workers in the process pool.
    For every build action there is worker which makes the analysis.
    """

    # Handle SIGINT to stop this script running.
    def signal_handler(*arg, **kwarg):
        try:
            pool.terminate()
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

    try:
        # Workaround, equivalent of map.
        # The main script does not get signal
        # while map or map_async function is running.
        # It is a python bug, this does not happen if a timeout is specified;
        # then receive the interrupt immediately.

        analyzed_actions = [(build_action,
                             context,
                             analyzer_config_map,
                             output_path,
                             skip_handler) for build_action in actions]

        pool.map_async(check,
                       analyzed_actions,
                       1,
                       callback=lambda results: worker_result_handler(
                           results, metadata, output_path)
                       ).get(float('inf'))

        pool.close()
    except Exception:
        pool.terminate()
        raise
    finally:
        pool.join()
