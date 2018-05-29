# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
"""

from collections import defaultdict
import codecs
import glob
import multiprocessing
import os
import shutil
import signal
import sys
import traceback
import zipfile

from libcodechecker import util
from libcodechecker.analyze import analyzer_env
from libcodechecker.analyze import plist_parser
from libcodechecker.analyze.analyzers import analyzer_clangsa
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.analyze.statistics_collector \
    import SpecialReturnValueCollector
from libcodechecker.analyze.statistics_collector \
    import ReturnValueCollector
from libcodechecker.logger import get_logger

LOG = get_logger('analyzer')


def worker_result_handler(results, metadata, output_path):
    """
    Print the analysis summary.
    """

    if metadata is None:
        metadata = {}

    successful_analysis = defaultdict(int)
    failed_analysis = defaultdict(int)
    skipped_num = 0
    reanalyzed_num = 0

    for res, skipped, reanalyzed, analyzer_type, _ in results:
        if skipped:
            skipped_num += 1
        else:
            if reanalyzed:
                reanalyzed_num += 1

            if res == 0:
                successful_analysis[analyzer_type] += 1
            else:
                failed_analysis[analyzer_type] += 1

    LOG.info("----==== Summary ====----")
    LOG.info("Total analyzed compilation commands: %s", str(len(results)))
    if successful_analysis:
        LOG.info("Successfully analyzed")
        for analyzer_type, res in successful_analysis.items():
            LOG.info('  ' + analyzer_type + ': ' + str(res))

    if failed_analysis:
        LOG.info("Failed to analyze")
        for analyzer_type, res in failed_analysis.items():
            LOG.info('  ' + analyzer_type + ': ' + str(res))

    if reanalyzed_num:
        LOG.info("Reanalyzed compilation commands: " + str(reanalyzed_num))
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


def create_dependencies(action):
    """
    Transforms the given original build 'command' to a command that, when
    executed, is able to generate a dependency list.
    """

    def __eliminate_argument(arg_vect, opt_string, has_arg=False):
        """
        This call eliminates the parameters matching the given option string,
        along with its argument coming directly after the opt-string if any,
        from the command. The argument can possibly be separated from the flag.
        """
        while True:
            option_index = next(
                (i for i, c in enumerate(arg_vect)
                 if c.startswith(opt_string)), None)

            if option_index:
                separate = 1 if has_arg and \
                    len(arg_vect[option_index]) == len(opt_string) else 0
                arg_vect = arg_vect[0:option_index] + \
                    arg_vect[option_index + separate + 1:]
            else:
                break

        return arg_vect

    if 'CC_LOGGER_GCC_LIKE' not in os.environ:
        os.environ['CC_LOGGER_GCC_LIKE'] = 'gcc:g++:clang:clang++:cc:c++'

    command = action.original_command.split(' ')
    if any(binary_substring in command[0] for binary_substring
           in os.environ['CC_LOGGER_GCC_LIKE'].split(':')):
        # gcc and clang can generate makefile-style dependency list.

        # If an output file is set, the dependency is not written to the
        # standard output but rather into the given file.
        # We need to first eliminate the output from the command.
        command = __eliminate_argument(command, '-o', True)
        command = __eliminate_argument(command, '--output', True)

        # Remove potential dependency-file-generator options from the string
        # too. These arguments found in the logged build command would derail
        # us and generate dependencies, e.g. into the build directory used.
        command = __eliminate_argument(command, '-MM')
        command = __eliminate_argument(command, '-MF', True)
        command = __eliminate_argument(command, '-MP')
        command = __eliminate_argument(command, '-MT', True)
        command = __eliminate_argument(command, '-MQ', True)
        command = __eliminate_argument(command, '-MD')
        command = __eliminate_argument(command, '-MMD')

        # Clang contains some extra options.
        command = __eliminate_argument(command, '-MJ', True)
        command = __eliminate_argument(command, '-MV')

        # Build out custom invocation for dependency generation.
        command = [command[0], '-E', '-M', '-MT', '__dummy'] + command[1:]

        # Remove empty arguments
        command = [i for i in command if i]

        LOG.debug("Crafting build dependencies from GCC or Clang!")

        output, rc = util.call_command(command,
                                       env=os.environ,
                                       cwd=action.directory)
        output = codecs.decode(output, 'utf-8', 'replace')
        if rc == 0:
            # Parse 'Makefile' syntax dependency output.
            dependencies = output.replace('__dummy: ', '') \
                .replace('\\', '') \
                .replace('  ', '') \
                .replace(' ', '\n')

            # The dependency list already contains the source file's path.
            return [dep for dep in dependencies.split('\n') if dep != ""]
        else:
            raise IOError("Failed to generate dependency list for " +
                          ' '.join(command) + "\n\nThe original output was: " +
                          output)
    else:
        raise ValueError("Cannot generate dependency list for build "
                         "command '" + ' '.join(command) + "'")


# Progress reporting.
progress_checked_num = None
progress_actions = None


def init_worker(checked_num, action_num):
    global progress_checked_num, progress_actions
    progress_checked_num = checked_num
    progress_actions = action_num


def get_dependent_headers(buildaction, archive):
    LOG.debug("Generating dependent headers via compiler...")
    try:
        dependencies = set(create_dependencies(buildaction))
    except Exception as ex:
        LOG.debug("Couldn't create dependencies:")
        LOG.debug(str(ex))
        # TODO append with buildaction
        archive.writestr("no-sources", str(ex))
        dependencies = set()
    return dependencies


def collect_debug_data(zip_file, other_files, buildaction, out, err,
                       original_command, analyzer_cmd, analyzer_returncode,
                       action_directory, action_target, actions_map):
    """
    Collect analysis and build system information which can be used
    to reproduce the failed analysis.
    """
    with zipfile.ZipFile(zip_file, 'w') as archive:
        LOG.debug("[ZIP] Writing analyzer STDOUT to /stdout")
        archive.writestr("stdout", out)

        LOG.debug("[ZIP] Writing analyzer STDERR to /stderr")
        archive.writestr("stderr", err)

        dependencies = get_dependent_headers(buildaction,
                                             archive)

        mentioned_files_dependent_files = set()
        for of in other_files:
            mentioned_file = os.path.abspath(
                os.path.join(action_directory, of))
            # Use the target of the original build action.
            key = mentioned_file, action_target
            mentioned_file_action = actions_map.get(key)
            if mentioned_file_action is not None:
                mentioned_file_deps = get_dependent_headers(
                    mentioned_file_action, archive)
                mentioned_files_dependent_files.\
                    update(mentioned_file_deps)
            else:
                LOG.debug("Could not find {0} in build actions."
                          .format(key))

        dependencies.update(other_files)
        dependencies.update(mentioned_files_dependent_files)

        # `dependencies` might contain absolute and relative paths
        # for the same file, so make everything absolute by
        # joining with the the absolute action.directory.
        # If `dependent_source` is absolute it remains absolute
        # after the join, as documented on docs.python.org .
        dependencies_copy = set()
        for dependent_source in dependencies:
            dependent_source = os.path.join(action_directory,
                                            dependent_source)
            dependencies_copy.add(dependent_source)
        dependencies = dependencies_copy

        LOG.debug("Writing dependent files to archive.")
        for dependent_source in dependencies:
            LOG.debug("[ZIP] Writing '" + dependent_source + "' "
                      "to the archive.")
            archive_subpath = dependent_source.lstrip('/')

            archive_path = os.path.join('sources-root',
                                        archive_subpath)
            try:
                _ = archive.getinfo(archive_path)
                LOG.debug("[ZIP] '{0}' is already in the ZIP "
                          "file, won't add it again!"
                          .format(archive_path))
                continue
            except KeyError:
                # If the file is already contained in the ZIP,
                # a valid object is returned, otherwise a KeyError
                # is raised.
                pass

            try:
                archive.write(dependent_source,
                              archive_path,
                              zipfile.ZIP_DEFLATED)
            except Exception as ex:
                # In certain cases, the output could contain
                # invalid tokens (such as error messages that were
                # printed even though the dependency generation
                # returned 0).
                LOG.debug("[ZIP] Couldn't write, because " +
                          str(ex))
                archive.writestr(
                    os.path.join('failed-sources-root',
                                 archive_subpath),
                    "Couldn't write this file, because:\n" +
                    str(ex))

        LOG.debug("[ZIP] Writing extra information...")

        archive.writestr("build-action", original_command)
        archive.writestr("analyzer-command", ' '.join(analyzer_cmd))
        archive.writestr("return-code", str(analyzer_returncode))


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


def prepare_check(source, action, analyzer_config_map, output_dir,
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

    if action.analyzer_type == analyzer_types.CLANG_SA and statistics_data:
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

        source_analyzer.config_handler.enable_checker(
            SpecialReturnValueCollector.checker_analyze)

        source_analyzer.config_handler.enable_checker(
            ReturnValueCollector.checker_analyze)

    # Source is the currently analyzed source file
    # there can be more in one buildaction.
    source_analyzer.source_file = source

    # The result handler for analysis is an empty result handler
    # which only returns metadata, but can't process the results.
    rh = analyzer_types.construct_analyze_handler(action,
                                                  output_dir,
                                                  severity_map,
                                                  skip_handler)

    # NOTICE!
    # The currently analyzed source file needs to be set before the
    # analyzer command is constructed.
    # The analyzer output file is based on the currently
    # analyzed source.
    rh.analyzed_source_file = source

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


def handle_failure(source_analyzer, rh, action, zip_file,
                   result_base, actions_map):
    """
    If the analysis fails a debug zip is packed together which contains
    build, analysis information and source files to be able to
    reproduce the failed analysis.
    """
    other_files = set()

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

    collect_debug_data(zip_file,
                       other_files,
                       rh.buildaction,
                       rh.analyzer_stdout,
                       rh.analyzer_stderr,
                       action.original_command,
                       rh.analyzer_cmd,
                       rh.analyzer_returncode,
                       action.directory,
                       action.target,
                       actions_map)
    LOG.debug("ZIP file written at '" + zip_file + "'")

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

    skipped = False
    reanalyzed = False

    failed_dir = output_dirs["failed"]
    success_dir = output_dirs["success"]

    try:
        # If one analysis fails the check fails.
        return_codes = 0
        skipped = False

        result_file = ''
        for source in action.sources:

            # If there is no skiplist handler there was no skip list file
            # in the command line.
            # C++ file skipping is handled here.
            source_file_name = os.path.basename(source)

            if skip_handler and skip_handler.should_skip(source):
                LOG.debug_analyzer(source_file_name + ' is skipped')
                skipped = True
                continue

            source = util.escape_source_path(source)

            source_analyzer, analyzer_cmd, rh, reanalyzed = \
                prepare_check(source, action, analyzer_config_map,
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
                        analyzer_process, analysis_timeout, signal.SIGABRT)
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
                            "of {0} seconds.".format(analysis_timeout))
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

            ctu_suffix = 'CTU'
            zip_suffix = ctu_suffix if ctu_active else ''

            zip_file = result_base + zip_suffix + '.zip'
            zip_file = os.path.join(failed_dir, zip_file)

            ctu_zip_file = result_base + ctu_suffix + '.zip'
            ctu_zip_file = os.path.join(failed_dir, ctu_zip_file)

            return_codes = rh.analyzer_returncode
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
                LOG.info("[%d/%d] %s analyzed %s successfully." %
                         (progress_checked_num.value, progress_actions.value,
                          action.analyzer_type, source_file_name))

                if skip_handler:
                    # We need to check the plist content because skipping
                    # reports in headers can be done only this way.
                    plist_parser.skip_report_from_plist(result_file,
                                                        skip_handler)

            else:
                LOG.error("Analyzing '" + source_file_name + "' with " +
                          action.analyzer_type +
                          " CTU" if ctu_active else " " + "failed.")

                if not quiet_output_on_stdout:
                    LOG.error('\n' + rh.analyzer_stdout)
                    LOG.error('\n' + rh.analyzer_stderr)

                handle_failure(source_analyzer, rh, action, zip_file,
                               result_base, actions_map)

                if ctu_active and ctu_reanalyze_on_failure:
                    LOG.error("Try to reanalyze without CTU")
                    # Try to reanalyze with CTU disabled.
                    source_analyzer, analyzer_cmd, rh, reanalyzed = \
                        prepare_check(source, action,
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
                                       success_dir, zipfile)

                        msg = "[{0}/{1}] {2} analyzed {3} without" \
                            " CTU successfully.".format(
                                progress_checked_num.value,
                                progress_actions.value,
                                action.analyzer_type,
                                source_file_name)

                        LOG.info(msg)
                    else:
                        LOG.error("Analyzing '" + source_file_name +
                                  "' with " + action.analyzer_type +
                                  " without CTU failed.")

                        zip_file = result_base + '.zip'
                        zip_file = os.path.join(failed_dir, zip_file)
                        handle_failure(source_analyzer, rh, action,
                                       zip_file, result_base, actions_map)

            if not quiet_output_on_stdout:
                if rh.analyzer_returncode:
                    LOG.error('\n' + rh.analyzer_stdout)
                    LOG.error('\n' + rh.analyzer_stderr)
                else:
                    LOG.debug_analyzer('\n' + rh.analyzer_stdout)
                    LOG.debug_analyzer('\n' + rh.analyzer_stderr)

        progress_checked_num.value += 1

        return return_codes, skipped, reanalyzed, action.analyzer_type, \
            result_file

    except Exception as e:
        LOG.debug_analyzer(str(e))
        traceback.print_exc(file=sys.stdout)
        return 1, skipped, reanalyzed, action.analyzer_type, None


def start_workers(actions_map, actions, context, analyzer_config_map,
                  jobs, output_path, skip_handler, metadata,
                  quiet_analyze, capture_analysis_output, timeout,
                  ctu_reanalyze_on_failure, statistics_data):
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
    analyzer_environment = analyzer_env.get_check_env(
        context.path_env_extra,
        context.ld_lib_path_extra)

    try:
        # Workaround, equivalent of map.
        # The main script does not get signal
        # while map or map_async function is running.
        # It is a python bug, this does not happen if a timeout is specified;
        # then receive the interrupt immediately.

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

    if not os.listdir(success_dir):
        shutil.rmtree(success_dir)

    if not os.listdir(failed_dir):
        shutil.rmtree(failed_dir)
