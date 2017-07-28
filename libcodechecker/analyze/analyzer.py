# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Prepare and start different analysis types
"""
import copy
import os
import shlex
import shutil
import subprocess
import time

from libcodechecker.logger import LoggerFactory
from libcodechecker.analyze import analysis_manager
from libcodechecker.analyze import analyzer_env
from libcodechecker.analyze import skiplist_handler
from libcodechecker.analyze.analyzers import analyzer_types

LOG = LoggerFactory.get_new_logger('ANALYZER')


def prepare_actions(actions, enabled_analyzers):
    """
    Set the analyzer type for each buildaction.
    Multiple actions if multiple source analyzers are set.
    """
    res = []

    for ea in enabled_analyzers:
        for action in actions:
            new_action = copy.deepcopy(action)
            new_action.analyzer_type = ea
            res.append(new_action)
    return res


def __get_analyzer_version(context, analyzer_config_map):
    """
    Get the path and the version of the analyzer binaries.
    """
    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    # Get the analyzer binaries from the config_map which
    # contains only the checked and available analyzers.
    versions = {}
    for _, analyzer_cfg in analyzer_config_map.items():
        analyzer_bin = analyzer_cfg.analyzer_binary
        version = [analyzer_bin, u' --version']
        try:
            output = subprocess.check_output(shlex.split(' '.join(version)),
                                             env=check_env)
            versions[analyzer_bin] = output
        except (subprocess.CalledProcessError, OSError) as oerr:
            LOG.warning("Failed to get analyzer version: " + ' '.join(version))
            LOG.warning(oerr.strerror)

    return versions


def __get_skip_handler(args):
    try:
        if args.skipfile:
            LOG.debug_analyzer("Creating skiplist handler.")
            return skiplist_handler.SkipListHandler(args.skipfile)
    except AttributeError:
        LOG.debug_analyzer('Skip file was not set in the command line')


def perform_analysis(args, context, actions, metadata):
    """
    Perform static analysis via the given (or if not, all) analyzers,
    in the given analysis context for the supplied build actions.
    Additionally, insert statistical information into the metadata dict.
    """

    analyzers = args.analyzers if 'analyzers' in args \
        else analyzer_types.supported_analyzers
    analyzers, _ = analyzer_types.check_supported_analyzers(
        analyzers, context)

    ctu_collect = False
    ctu_analyze = False
    ctu_dir = ''
    ctu_func_map_cmd = ''
    # ctu_in_memory = False
    if hasattr(args, 'ctu_phases'):
        args.ctu_dir = os.path.abspath(args.ctu_dir)
        ctu_collect = args.ctu_phases[0]
        ctu_analyze = args.ctu_phases[1]
        ctu_dir = args.ctu_dir
        ctu_func_map_cmd = args.ctu_func_map_cmd
        # ctu_in_memory = args.ctu_in_memory
        if analyzer_types.CLANG_SA not in analyzers:
            LOG.error("CTU can only be used together with the static analyzer")
            return

    actions = prepare_actions(actions, analyzers)
    config_map = analyzer_types.build_config_handlers(args, context, analyzers)

    # Save some metadata information.
    versions = __get_analyzer_version(context, config_map)
    metadata['versions'].update(versions)

    metadata['checkers'] = {}
    for analyzer in analyzers:
        metadata['checkers'][analyzer] = []

        for check, data in config_map[analyzer].checks().items():
            enabled, _ = data
            if not enabled:
                continue
            metadata['checkers'][analyzer].append(check)

    if ctu_collect:
        shutil.rmtree(ctu_dir, ignore_errors=True)
    elif ctu_analyze and not os.path.exists(ctu_dir):
        LOG.error("The given <ctu-dir> '" + ctu_dir + "' does not exist")
        return

    # Run analysis.
    LOG.info("Starting static analysis ...")
    start_time = time.time()

    analysis_manager.start_workers(actions, context, config_map,
                                   args.jobs, args.output_path,
                                   __get_skip_handler(args), metadata,
                                   ctu_collect, ctu_analyze,
                                   ctu_dir, ctu_func_map_cmd)

    end_time = time.time()
    LOG.info("Analysis length: " + str(end_time - start_time) + " sec.")

    metadata['timestamps'] = {'begin': start_time,
                              'end': end_time}

    if ctu_collect and ctu_analyze:
        shutil.rmtree(ctu_dir, ignore_errors=True)
