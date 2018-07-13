# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""
Supported analyzer types.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import os
import platform
import re
import sys

from libcodechecker.analyze import analyzer_env
from libcodechecker.analyze import host_check
from libcodechecker.analyze.analyzers import analyzer_clang_tidy
from libcodechecker.analyze.analyzers import analyzer_clangsa
from libcodechecker.analyze.analyzers import config_handler_clang_tidy
from libcodechecker.analyze.analyzers import config_handler_clangsa
from libcodechecker.analyze.analyzers import result_handler_base
from libcodechecker.analyze.analyzers import result_handler_clang_tidy
from libcodechecker.logger import get_logger

LOG = get_logger('analyzer')

CLANG_SA = 'clangsa'
CLANG_TIDY = 'clang-tidy'

supported_analyzers = {CLANG_SA, CLANG_TIDY}


def check_supported_analyzers(analyzers, context):
    """
    Checks the given analyzers in the current context for their executability
    and support in CodeChecker.

    This method also updates the given context.analyzer_binaries if the
    context's configuration is bogus but had been resolved.

    :return: (enabled, failed) where enabled is a list of analyzer names
     and failed is a list of (analyzer, reason) tuple.
    """

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    analyzer_binaries = context.analyzer_binaries

    enabled_analyzers = set()
    failed_analyzers = set()

    for analyzer_name in analyzers:
        if analyzer_name not in supported_analyzers:
            failed_analyzers.add((analyzer_name,
                                  "Analyzer unsupported by CodeChecker."))

        # Get the compiler binary to check if it can run.
        available_analyzer = True
        analyzer_bin = analyzer_binaries.get(analyzer_name)
        if not analyzer_bin:
            failed_analyzers.add((analyzer_name,
                                  "Failed to detect analyzer binary."))
            available_analyzer = False
        elif not os.path.isabs(analyzer_bin):
            # If the analyzer is not in an absolute path, try to find it...
            if analyzer_name == CLANG_SA:
                found_bin = analyzer_clangsa.ClangSA. \
                    resolve_missing_binary(analyzer_bin, check_env)
            elif analyzer_name == CLANG_TIDY:
                found_bin = analyzer_clang_tidy.ClangTidy. \
                    resolve_missing_binary(analyzer_bin, check_env)

            # found_bin is an absolute path, an executable in one of the
            # PATH folders.
            # If found_bin is the same as the original binary, ie., normally
            # calling the binary without any search would have resulted in
            # the same binary being called, it's NOT a "not found".
            if found_bin and os.path.basename(found_bin) != analyzer_bin:
                LOG.debug("Configured binary '{0}' for analyzer '{1}' was "
                          "not found, but environment PATH contains '{2}'."
                          .format(analyzer_bin, analyzer_name, found_bin))
                context.analyzer_binaries[analyzer_name] = found_bin

            if not found_bin or \
                    not host_check.check_clang(found_bin, check_env):
                # If analyzer_bin is not False here, the resolver found one.
                failed_analyzers.add((analyzer_name,
                                      "Couldn't run analyzer binary."))
                available_analyzer = False
        elif not host_check.check_clang(analyzer_bin, check_env):
            # Analyzers unavailable under absolute paths are deliberately a
            # configuration problem.
            failed_analyzers.add((analyzer_name,
                                  "Cannot execute analyzer binary."))
            available_analyzer = False

        if available_analyzer:
            enabled_analyzers.add(analyzer_name)

    return enabled_analyzers, failed_analyzers


def construct_analyzer_type(analyzer_type, config_handler, buildaction):
    """
    Construct a specific analyzer based on the type.
    """

    LOG.debug_analyzer('Constructing ' + analyzer_type + '  analyzer')
    if analyzer_type == CLANG_SA:
        analyzer = analyzer_clangsa.ClangSA(config_handler,
                                            buildaction)
        return analyzer

    elif analyzer_type == CLANG_TIDY:
        analyzer = analyzer_clang_tidy.ClangTidy(config_handler,
                                                 buildaction)
        return analyzer

    LOG.error('Unsupported analyzer type: ' + analyzer_type)
    return None


def construct_analyzer(buildaction,
                       analyzer_config_map):
    """
    Construct an analyzer.
    """
    try:
        analyzer_type = buildaction.analyzer_type
        # Get the proper config handler for this analyzer type.
        config_handler = analyzer_config_map.get(analyzer_type)

        analyzer = construct_analyzer_type(analyzer_type,
                                           config_handler,
                                           buildaction)
        return analyzer

    except Exception as ex:
        LOG.debug_analyzer(ex)
        return None


def gen_name_variations(checkers):
    """
    Generate all applicable name variations from the given checker list.
    """
    checker_names = [name for name, _ in checkers]
    reserved_names = []

    for name in checker_names:
        delim = '.' if '.' in name else '-'
        parts = name.split(delim)
        # Creates a list of variations from a checker name, e.g.
        # ['security', 'security.insecureAPI', 'security.insecureAPI.gets']
        # from 'security.insecureAPI.gets' or
        # ['misc', 'misc-dangling', 'misc-dangling-handle']
        # from 'misc-dangling-handle'.
        variations = [delim.join(parts[:(i + 1)]) for i in range(len(parts))]
        reserved_names += variations

    return reserved_names


def initialize_checkers(config_handler,
                        available_profiles,
                        package_root,
                        checkers,
                        checker_config=None,
                        cmdline_checkers=None,
                        enable_all=False):
    """
    Initializes the checker list for the specified config handler based
    on given checker profiles, commandline arguments and the analyzer-retrieved
    checker list.
    """

    # By default disable all checkers.
    for checker_name, description in checkers:
        config_handler.add_checker(checker_name, False, description)

    # Set default enabled or disabled checkers, retrieved from the config file.
    if checker_config:
        # Check whether a default profile exists.
        profile_lists = checker_config.values()
        all_profiles = [
            profile for check_list in profile_lists for profile in check_list]
        if 'default' not in all_profiles:
            LOG.warning("No default profile found!")
        else:
            # Turn default checkers on.
            for checker_name, profile_list in checker_config.items():
                if 'default' in profile_list:
                    config_handler.enable_checker(checker_name)

    # If enable_all is given, almost all checkers should be enabled.
    if enable_all:
        for checker_name, enabled in checkers:
            if not checker_name.startswith("alpha.") and \
                    not checker_name.startswith("debug.") and \
                    not checker_name.startswith("osx."):
                # There are a few exceptions, though, which still need to
                # be manually enabled by the user: alpha and debug.
                config_handler.enable_checker(checker_name)

            if checker_name.startswith("osx.") and \
                    platform.system() == 'Darwin':
                # OSX checkers are only enable-all'd if we are on OSX.
                config_handler.enable_checker(checker_name)

    # Set user defined enabled or disabled checkers from the command line.
    if cmdline_checkers:

        # Construct a list of reserved checker names.
        # (It is used to check if a profile name is valid.)
        reserved_names = gen_name_variations(checkers)

        for identifier, enabled in cmdline_checkers:

            # The identifier is a profile name.
            if identifier in available_profiles:
                profile_name = identifier

                if profile_name == "list":
                    LOG.error("'list' is a reserved profile keyword. ")
                    LOG.error("Please choose another profile name in "
                              "'{0}'/config/config.json and rebuild."
                              .format(package_root))
                    sys.exit(1)

                if profile_name in reserved_names:
                    LOG.error("Profile name '" + profile_name + "' conflicts "
                              "with a checker(-group) name.")
                    LOG.error("Please choose another profile name in "
                              "'{0}'/config/config.json and rebuild."
                              .format(package_root))
                    sys.exit(1)

                profile_checkers = [name for name, profile_list
                                    in checker_config.items()
                                    if profile_name in profile_list]
                for checker_name in profile_checkers:
                    if enabled:
                        config_handler.enable_checker(checker_name)
                    else:
                        config_handler.disable_checker(checker_name)

            # The identifier is a checker(-group) name.
            else:
                checker_name = identifier
                if enabled:
                    config_handler.enable_checker(checker_name)
                else:
                    config_handler.disable_checker(checker_name)


def __replace_env_var(cfg_file):
    def replacer(matchobj):
        env_var = matchobj.group(1)
        if matchobj.group(1) not in os.environ:
            LOG.error(env_var + ' environment variable not set in ' + cfg_file)
            return ''
        return os.environ[env_var]

    return replacer


def __get_compiler_resource_dir(context, analyzer_binary):
    resource_dir = ''
    if len(context.compiler_resource_dir) > 0:
        resource_dir = context.compiler_resource_dir
    # If not set then ask the binary for the resource dir.
    else:
        # Can be None if Clang is too old.
        resource_dir = host_check.get_resource_dir(analyzer_binary)
        if resource_dir is None:
            resource_dir = ""
    return resource_dir


def __build_clangsa_config_handler(args, context):
    """
    Build the config handler for clang static analyzer.
    Handle config options from the command line and config files.
    """

    config_handler = config_handler_clangsa.ClangSAConfigHandler()
    config_handler.analyzer_plugins_dir = context.checker_plugin
    config_handler.analyzer_binary = context.analyzer_binaries.get(CLANG_SA)
    config_handler.compiler_resource_dir =\
        __get_compiler_resource_dir(context, config_handler.analyzer_binary)

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    if 'ctu_phases' in args:
        config_handler.ctu_dir = os.path.join(args.output_path,
                                              args.ctu_dir)

        config_handler.ctu_has_analyzer_display_ctu_progress = \
            host_check.has_analyzer_feature(
                context.analyzer_binaries.get(CLANG_SA),
                '-analyzer-display-ctu-progress',
                check_env)
        config_handler.log_file = args.logfile
        config_handler.path_env_extra = context.path_env_extra
        config_handler.ld_lib_path_extra = context.ld_lib_path_extra

    try:
        with open(args.clangsa_args_cfg_file, 'rb') as sa_cfg:
            sa_args = re.sub(r'\$\((.*?)\)',
                             __replace_env_var(args.clangsa_args_cfg_file),
                             sa_cfg.read().strip()).split(' ')

            # For backward compatibility we filter out -Xclang options.
            filtered_sa_args = filter(lambda x: x != '-Xclang', sa_args)

            # We -Xclang flag before every value of configuration switch.
            config_handler.analyzer_extra_arguments = \
                ' '.join(['-Xclang ' + arg for arg in filtered_sa_args])
    except IOError as ioerr:
        LOG.debug_analyzer(ioerr)
    except AttributeError as aerr:
        # No clangsa arguments file was given in the command line.
        LOG.debug_analyzer(aerr)

    analyzer = construct_analyzer_type(CLANG_SA, config_handler, None)

    checkers = analyzer.get_analyzer_checkers(config_handler, check_env)

    # Read clang-sa checkers from the config file.
    clang_sa_checkers = context.checker_config.get(CLANG_SA + '_checkers')

    try:
        cmdline_checkers = args.ordered_checkers
    except AttributeError:
        LOG.debug_analyzer('No checkers were defined in '
                           'the command line for ' + CLANG_SA)
        cmdline_checkers = None

    initialize_checkers(config_handler,
                        context.available_profiles,
                        context.package_root,
                        checkers,
                        clang_sa_checkers,
                        cmdline_checkers,
                        'enable_all' in args and args.enable_all)

    return config_handler


def __build_clang_tidy_config_handler(args, context):
    """
    Build the config handler for clang tidy analyzer.
    Handle config options from the command line and config files.
    """

    config_handler = config_handler_clang_tidy.ClangTidyConfigHandler()
    config_handler.analyzer_binary = context.analyzer_binaries.get(CLANG_TIDY)

    # FIXME We cannot get the resource dir from the clang-tidy binary,
    # therefore now we get a clang binary which is a sibling of the clang-tidy.
    # TODO Support "clang-tidy -print-resource-dir" .
    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)
    # Overwrite PATH to contain only the parent of the clang binary.
    if os.path.isabs(config_handler.analyzer_binary):
        check_env['PATH'] = os.path.dirname(config_handler.analyzer_binary)
    clang_bin = analyzer_clangsa.ClangSA.resolve_missing_binary('clang',
                                                                check_env)
    if os.path.isfile(clang_bin):
        config_handler.compiler_resource_dir =\
            __get_compiler_resource_dir(context, clang_bin)
    else:
        config_handler.compiler_resource_dir =\
            __get_compiler_resource_dir(context,
                                        config_handler.analyzer_binary)

    try:
        with open(args.tidy_args_cfg_file, 'rb') as tidy_cfg:
            config_handler.analyzer_extra_arguments = \
                re.sub(r'\$\((.*?)\)', __replace_env_var,
                       tidy_cfg.read().strip())
    except IOError as ioerr:
        LOG.debug_analyzer(ioerr)
    except AttributeError as aerr:
        # No clang tidy arguments file was given in the command line.
        LOG.debug_analyzer(aerr)

    analyzer = construct_analyzer_type(CLANG_TIDY, config_handler, None)
    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    checkers = analyzer.get_analyzer_checkers(config_handler, check_env)

    # Read clang-tidy checkers from the config file.
    clang_tidy_checkers = context.checker_config.get(CLANG_TIDY + '_checkers')

    try:
        cmdline_checkers = args.ordered_checkers
    except AttributeError:
        LOG.debug_analyzer('No checkers were defined in '
                           'the command line for ' +
                           CLANG_TIDY)
        cmdline_checkers = None

    initialize_checkers(config_handler,
                        context.available_profiles,
                        context.package_root,
                        checkers,
                        clang_tidy_checkers,
                        cmdline_checkers,
                        'enable_all' in args and args.enable_all)

    return config_handler


def build_config_handlers(args, context, enabled_analyzers):
    """

    Handle config from command line or from config file if no command line
    config is given.

    Supported command line config format is in JSON tidy supports YAML also but
    no standard lib for yaml parsing is available in python.
    """

    analyzer_config_map = {}

    for ea in enabled_analyzers:
        if ea == CLANG_SA:
            config_handler = __build_clangsa_config_handler(args, context)
        elif ea == CLANG_TIDY:
            config_handler = __build_clang_tidy_config_handler(args, context)
        else:
            LOG.debug("Unhandled analyzer: " + str(ea))
        analyzer_config_map[ea] = config_handler

    return analyzer_config_map


def construct_analyze_handler(buildaction,
                              report_output,
                              severity_map,
                              skiplist_handler):
    """
    Construct an empty (base) ResultHandler which is capable of returning
    analyzer worker statuses to the caller method, but does not provide
    actual parsing and processing of results, instead only saves the analysis
    results.
    """
    if buildaction.analyzer_type not in supported_analyzers:
        return None

    if buildaction.analyzer_type == CLANG_SA:
        res_handler = result_handler_base.ResultHandler(buildaction,
                                                        report_output)
    elif buildaction.analyzer_type == CLANG_TIDY:
        res_handler = result_handler_clang_tidy.ClangTidyPlistToFile(
            buildaction, report_output)

    res_handler.severity_map = severity_map
    res_handler.skiplist_handler = skiplist_handler
    return res_handler
