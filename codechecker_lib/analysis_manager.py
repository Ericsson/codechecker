# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
'''
'''

import os
import sys
import signal
import multiprocessing
import ntpath
import traceback

import shared

from codechecker_lib import logger
from codechecker_lib import analyzer_env
from codechecker_lib import result_handler

from codechecker_lib.database_handler import SQLServer

from codechecker_lib.analyzers import analyzer_types
from codechecker_lib.analyzers import analyzer_config_handler
from codechecker_lib.analyzers import analyzer_clangsa
from codechecker_lib.analyzers import analyzer_clang_tidy

LOG = logger.get_new_logger('ANALISYS MANAGER')


def construct_analyzer(buildaction,
                       analyzer_config_map):
    """
    construct an analyzer
    """
    try:

        analyzer_type = buildaction.analyzer_type

        if analyzer_type == analyzer_types.CLANG_SA:
            LOG.debug('Constructing clangSA analyzer')

            # get the proper config handler for this analyzer
            config_handler = analyzer_config_map.get(analyzer_type)

            analyzer = analyzer_clangsa.ClangSA(config_handler,
                                                buildaction)

            return analyzer

        elif analyzer_type == analyzer_types.CLANG_TIDY:
            LOG.debug("Constructing clang-tidy analyzer")

            config_handler = analyzer_config_map.get(analyzer_type)

            # TODO create clang tidy analyzer

            return None
        else:
            LOG.error('Not supported analyzer type')
            return None

    except Exception as ex:
        LOG.debug(ex)


def prepare_actions(actions, enabled_analyzers):
    """
    set the analyzer type for each buildaction
    muliply actions if multiple source analyzers are used
    """
    LOG.debug('Preparing build actions ...')
    res = []
    for ea in enabled_analyzers:
        for action in actions:
            action.analyzer_type = ea
            res.append(action)
    return res


def store_config_to_db(run_id, connection, configs):
    configuration_list = []
    for checker_name, key, key_value in configs:
        configuration_list.append(shared.ttypes.ConfigValue(checker_name,
                                                            key,
                                                            key_value))
    # store clangSA config to the database
    connection.add_config_info(run_id, configs)


def get_config_handler(args, context, enabled_analyzers, connection=None):
    """
    construct multiple config handlers and if there is a connection
    store configs into the database

    handle config from command line or from config file if no command line
    config is given

    supported command line config format is in JSON tidy supports YAML also but
    no standard lib for yaml parsing is available in python

    """

    run_id = context.run_id
    analyzer_config_map = {}

    for ea in enabled_analyzers:
        if ea == analyzer_types.CLANG_SA:
            config = ''
            if args.clangsa_config:
                # json format from command line
                if os.isfile(args.clangsa_config):
                    with open(args.clangsa_config) as conf:
                        config = conf.read()
                else:
                    config = args.clangsa_config
            else:
                # json format from config file from the package
                pass

            config_handler = analyzer_config_handler.construct_config_handler(args,
                                                                              context,
                                                                              ea,
                                                                              config)
            # extend analyzer config with
            # read clangsa checkers from the config file
            for data in context.default_checkers_config['clangsa_checkers']:
                config_handler.add_checks(data.items())

            # add user defined checkers in the command line
            try:
                config_handler.add_checks(args.ordered_checker_args)
            except AttributeError:
                LOG.debug('No checkers were defined in the command line for clangSA')

            LOG.debug(config_handler.checks())

            configs = config_handler.get_configs()
            if connection:
                store_config_to_db(run_id, connection, configs)
            analyzer_config_map[ea] = config_handler

        elif ea == analyzer_types.CLANG_TIDY:
            config = ''
            if args.clang_tidy_config:
                # json format from command line
                if os.isfile(args.clang_tidy_config):
                    with open(args.clang_tidy_config) as conf:
                        config = conf.read()
                else:
                    config = args.clang_tidy_config

                config_handler = analyzer_config_handler.construct_config_handler(args,
                                                                                  context,
                                                                                  ea,
                                                                                  config)
            else:
                # TODO read default config for clang tidy
                pass

            # extend analyzer config with
            # read clang-tidy checkers from the config file
            for data in context.default_checkers_config['clang_tidy_checkers']:
                config_handler.add_checks(data.items())

            # add user defined checkers in the command line
            try:
                config_handler.add_checks(args.tidy_checks)
            except AttributeError:
                LOG.debug('No checkers were defined in the command line for clang tidy')

            configs = config_handler.get_configs()
            if connection:
                store_config_to_db(run_id, connection, configs)
            analyzer_config_map[ea] = config_handler

    return analyzer_config_map


def worker_result_handler(results):
    """
    print the analisys summary
    """
    LOG.info("----==== Summary ====----")
    LOG.info("All/successed build actions: " +
             str(len(results)) + "/" +
             str(len(filter(lambda x: x == 0, results))))


def check(check_data):
    """
    Invoke clang with an action which called by processes.
    Different analyzer object belongs to for each build action

    skiplist handler is None if no skip file was configured
    """
    args, action, context, analyzer_config_map, skp_handler, \
        report_output_dir, use_db, keep_tmp = check_data

    try:
        # if one analysis fails the check fails
        return_codes = 0
        for source in action.sources:

            # if there is no skiplist handler there was no skip list file
            # in the command line
            # cpp file skipping is handled here
            _, source_file_name = ntpath.split(source)

            if skp_handler and skp_handler.should_skip(source):
                LOG.debug(source_file_name + ' is skipped')
                continue

            # construct analyzer env
            analyzer_environment = analyzer_env.get_check_env(context.path_env_extra,
                                                      context.ld_lib_path_extra)
            run_id = context.run_id

            rh = result_handler.construct_result_handler(args,
                                                         action,
                                                         run_id,
                                                         report_output_dir,
                                                         context.severity_map,
                                                         skp_handler,
                                                         use_db)

            #LOG.info('Analysing ' + source_file_name)

            # create a source analyzer
            source_analyzer = construct_analyzer(action,
                                                 analyzer_config_map)

            # source is the currently analyzed source file
            # there can be more in one buildaction
            source_analyzer.source_file = source

            # fills up the result handler with the analyzer information 
            source_analyzer.analyze(rh, analyzer_environment)

            analyzer_stderr = ''
            if rh.analyzer_returncode == 0:
                # analysis was successful
                # processing results
                if rh.analyzer_stdout != '':
                    LOG.debug('\n' + rh.analyzer_stdout)
                if rh.analyzer_stderr != '':
                    LOG.debug('\n' + rh.analyzer_stderr)
                rh.postprocess_result()
                rh.handle_results()
            else:
                # analisys failed
                if rh.analyzer_stdout != '':
                    LOG.error('\n' + rh.analyzer_stdout)
                if rh.analyzer_stderr != '':
                    LOG.error('\n' + rh.analyzer_stderr)
                return_codes = rh.analyzer_returncode

            if not keep_tmp:
                rh.clean_results()

        return return_codes

    except Exception as e:
        LOG.debug(str(e))
        traceback.print_exc(file=sys.stdout)
        return 1

def start_workers(args, actions, context, analyzer_config_map, skp_handler):
    """
    start the workers in the process pool
    for every buildaction there is worker which makes the analysis
    """

    # Handle SIGINT to stop this script running
    def signal_handler(*arg, **kwarg):
        try:
            pool.terminate()
        finally:
            sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    # create report output dir this will be used by the result handlers for each
    # analyzer to store analyzer results or temporary files
    # each analyzer instance does its own cleanup
    report_output = os.path.join(context.codechecker_workspace,
                                 context.report_output_dir_name)

    if not os.path.exists(report_output):
        os.mkdir(report_output)

    # Start checking parallel
    pool = multiprocessing.Pool(args.jobs)
    # pool.map(check, actions, 1)

    try:
        # Workaround, equialent of map
        # The main script does not get signal
        # while map or map_async function is running
        # It is a python bug, this does not happen if a timeout is specified;
        # then receive the interrupt immediately

        analyzed_actions = [(args,
                             build_action,
                             context,
                             analyzer_config_map,
                             skp_handler,
                             report_output,
                             True,
                             args.keep_tmp) for build_action in actions]

        pool.map_async(check,
                       analyzed_actions,
                       1,
                       callback=worker_result_handler).get(float('inf'))

        pool.close()
    except Exception:
        pool.terminate()
        raise
    finally:
        pool.join()
