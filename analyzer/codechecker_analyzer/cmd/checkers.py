# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
List the checkers available in the analyzers.
"""


import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from codechecker_report_converter import twodim

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.analyzers import analyzer_types
from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA
from codechecker_analyzer.analyzers.clangtidy.analyzer import ClangTidy

from codechecker_common import arg, logger
from codechecker_common.output import USER_FORMATS
from codechecker_common.checker_labels import CheckerLabels
from codechecker_analyzer import env
from codechecker_analyzer.analyzers.config_handler import CheckerState

LOG = logger.get_logger('system')


def get_diagtool_bin():
    """
    Return full path of diagtool.

    Select clang binary, check for a 'diagtool' binary next to the selected
    clang binary and return full path of this binary if it exists.
    """
    context = analyzer_context.get_context()
    clang_bin = context.analyzer_binaries.get(ClangSA.ANALYZER_NAME)

    if not clang_bin:
        return None

    # Resolve symlink.
    clang_bin = os.path.realpath(clang_bin)

    # Find diagtool next to the clang binary.
    diagtool_bin = os.path.join(os.path.dirname(clang_bin), 'diagtool')
    if os.path.exists(diagtool_bin):
        return diagtool_bin

    LOG.debug("'diagtool' can not be found next to the clang binary (%s)!",
              clang_bin)


def get_warnings(env=None):
    """
    Returns list of warning flags by using diagtool.
    """
    diagtool_bin = get_diagtool_bin()

    if not diagtool_bin:
        return []

    try:
        result = subprocess.check_output(
            [diagtool_bin, 'tree'],
            env=env,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore")
        return [w[2:] for w in result.split() if w.startswith("-W")]
    except (subprocess.CalledProcessError, OSError):
        return []


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    data_files_dir_path = analyzer_context.get_context().data_files_dir_path
    labels_dir_path = os.path.join(data_files_dir_path, 'config', 'labels')
    return {
        'prog': 'CodeChecker checkers',
        'formatter_class': arg.RawDescriptionDefaultHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Get the list of checkers available and their enabled "
                       "status in the supported analyzers.",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': """
The list of checkers that are enabled or disabled by default can be edited by
editing "profile:default" labels in the directory '{}'.

Example scenario: List checkers by labels
-----------------------------------------
List checkers in "sensitive" profile:
    CodeChecker checkers --label profile:sensitive
    CodeChecker checkers --profile sensitive

List checkers in "HIGH" severity:
    CodeChecker checkers --label severity:HIGH
    CodeChecker checkers --severity HIGH

List checkers covering str34-c SEI-CERT rule:
    CodeChecker checkers --label sei-cert:str-34-c
    CodeChecker checkers --guideline sei-cert:str34-c

List checkers covering all SEI-CERT rules:
    CodeChecker checkers --label guideline:sei-cert
    CodeChecker checkers --guideline sei-cert

List available profiles, guidelines and severities:
    CodeChecker checkers --profile
    CodeChecker checkers --guideline
    CodeChecker checkers --severity

List labels and their available values:
    CodeChecker checkers --label
    CodeChecker checkers --label severity
""".format(os.path.join(labels_dir_path)),

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "List the checkers available for code analysis."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('--analyzers',
                        nargs='+',
                        dest='analyzers',
                        metavar='ANALYZER',
                        required=False,
                        choices=analyzer_types.supported_analyzers,
                        default=list(analyzer_types.supported_analyzers.
                                     keys()),
                        help="Show checkers only from the analyzers "
                             "specified.")

    if get_diagtool_bin():
        parser.add_argument('-w', '--warnings',
                            dest='show_warnings',
                            default=argparse.SUPPRESS,
                            action='store_true',
                            required=False,
                            help="Show available warning flags.")

    parser.add_argument('--details',
                        dest='details',
                        default=argparse.SUPPRESS,
                        action='store_true',
                        required=False,
                        help="Show details about the checker, such as "
                             "status, checker name, analyzer name, severity, "
                             "guidelines and description. Status shows if the "
                             "checker is enabled besides the given labels. "
                             "If the labels don't trigger a checker then the "
                             "status is determined by the analyzer tool.")

    parser.add_argument('--label',
                        nargs='?',
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Filter checkers that are attached the given "
                             "label. The format of a label is "
                             "<label>:<value>. If no argument is given then "
                             "available labels are listed. If only <label> is "
                             "given then available values are listed.")

    parser.add_argument('--profile',
                        dest='profile',
                        nargs='?',
                        required=False,
                        default=argparse.SUPPRESS,
                        help="List checkers enabled by the selected profile. "
                             "If no argument is given then available profiles "
                             "are listed.")

    parser.add_argument('--guideline',
                        dest='guideline',
                        nargs='?',
                        required=False,
                        default=argparse.SUPPRESS,
                        help="List checkers that report on a specific "
                             "guideline. Without additional parameter, the "
                             "available guidelines and their corresponding "
                             "rules will be listed.")

    parser.add_argument('--severity',
                        dest='severity',
                        nargs='?',
                        required=False,
                        default=argparse.SUPPRESS,
                        help="List checkers with the given severity. Make "
                             "sure to indicate severity in capitals (e.g. "
                             "HIGH, MEDIUM, etc.) If no argument is given "
                             "then available severities are listed.")

    parser.add_argument('--checker-config',
                        dest='checker_config',
                        default=argparse.SUPPRESS,
                        action='store_true',
                        required=False,
                        help="Show checker configuration options for all "
                             "existing checkers supported by the analyzer. "
                             "These can be given to 'CodeChecker analyze "
                             "--checker-config'.")

    filters = parser.add_mutually_exclusive_group(required=False)

    # --only-enabled and --only-disabled flags are deprecated because they're
    # not used anymore. Earlier we listed all checkers that would be enabled
    # during analysis with the given filter set (--label, --profile,
    # --guideline) and that list contained default checkers among others which
    # were not explicitly enabled. (These could have been eliminated by
    # --only-enabled). Now we list only those checkers which fulfill the
    # conjunction of the provided labels, or we list all checkers if no filter
    # is given.
    filters.add_argument('--only-enabled',
                         dest='only_enabled',
                         default=argparse.SUPPRESS,
                         action='store_true',
                         help="DEPRECATED. Show only the enabled checkers.")

    filters.add_argument('--only-disabled',
                         dest='only_disabled',
                         default=argparse.SUPPRESS,
                         action='store_true',
                         help="DEPRECATED. Show only the disabled checkers.")

    parser.add_argument('-o', '--output',
                        dest='output_format',
                        required=False,
                        default='custom',
                        choices=USER_FORMATS + ['custom'],
                        help="The format to list the applicable checkers as.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def __uglify(text: str) -> str:
    """
    csv and json format output contain this non human readable header string:
    no CamelCase and no space.
    """
    return text.lower().replace(' ', '_')


def guideline_rules_for_checker(
    checker: str,
    context: analyzer_context.Context
) -> Dict[str, list]:
    """
    Returns the guideline and rules covered by the given checker. This
    function returns a dict which maps guideline names to the covered
    rules: { "sei-cert": ["arr30-c", ...], ... }.
    """
    result = defaultdict(list)
    labels = context.checker_labels.labels_of_checker(checker)
    guidelines = context.checker_labels.get_description('guideline')

    for label in labels:
        if label[0] in guidelines:
            result[label[0]].append(label[1])

    return result


def __guideline_to_label(
    args: argparse.Namespace,
    cl: CheckerLabels
) -> str:
    """
    Transforms --guideline parameter as if they were given through --label.
    For example "--guideline sei-cert" is equivalent with
    "--label guideline:sei-cert" and "--guideline sei-cert:str38-c" is the same
    as "--label sei-cert:str38-c".
    """
    guidelines = []
    for analyzer in args.analyzers:
        guidelines.extend(cl.occurring_values('guideline', analyzer))

    if args.guideline in guidelines:
        return f'guideline:{args.guideline}'
    else:
        if args.guideline.find(':') == -1:
            LOG.error('--guideline parameter is either <guideline> or '
                      '<guideline>:<rule>')
            sys.exit(1)
        return args.guideline


def __get_detailed_checker_info(
    args: argparse.Namespace,
    cl: CheckerLabels
) -> Dict[str, list]:
    """
    Returns a dictionary which maps analyzer names to the collection of their
    supported checkers. Checker information is described with tuples of this
    information: (status, checker name, analyzer name, description, labels).
    """
    context = analyzer_context.get_context()

    working_analyzers, _ = analyzer_types.check_supported_analyzers(
        analyzer_types.supported_analyzers,
        context)

    analyzer_config_map = analyzer_types.build_config_handlers(
        args, context, working_analyzers)

    analyzer_environment = env.extend(
        context.path_env_extra,
        context.ld_lib_path_extra)

    checker_info = defaultdict(list)

    for analyzer in working_analyzers:
        config_handler = analyzer_config_map.get(analyzer)
        analyzer_class = analyzer_types.supported_analyzers[analyzer]

        checkers = analyzer_class.get_analyzer_checkers(
            config_handler, analyzer_environment)

        profile_checkers = []
        if 'profile' in args:
            available_profiles = cl.get_description('profile')

            if args.profile not in available_profiles:
                LOG.error("Checker profile '%s' does not exist!",
                          args.profile)
                LOG.error("To list available profiles, use '--profile list'.")
                sys.exit(1)

            profile_checkers.append((f'profile:{args.profile}', True))

        if 'label' in args:
            profile_checkers.extend((label, True) for label in args.label)

        if 'severity' in args:
            profile_checkers.append((f'severity:{args.severity}', True))

        if 'guideline' in args:
            profile_checkers.append((__guideline_to_label(args, cl), True))

        config_handler.initialize_checkers(
            context, checkers, profile_checkers)

        for checker, (state, description) in config_handler.checks().items():
            # severity = cl.severity(checker)
            # guideline = guideline_rules_for_checker(checker, context)
            # checker_info[analyzer].append(
            #     (state, checker, analyzer, severity, guideline, description))
            checker_info[analyzer].append(
                (state, checker, analyzer, description,
                 sorted(cl.labels_of_checker(checker, analyzer))))

    if 'show_warnings' in args:
        for warning in get_warnings(analyzer_environment):
            warning = 'clang-diagnostic-' + warning
            # guideline = guideline_rules_for_checker(warning, context)
            # checker_info[ClangTidy.ANALYZER_NAME].append(
            #     (CheckerState.default, warning, ClangTidy.ANALYZER_NAME,
            #      'MEDIUM', guideline, ''))
            checker_info[ClangTidy.ANALYZER_NAME].append(
                (CheckerState.default, warning, ClangTidy.ANALYZER_NAME, '',
                 sorted(cl.labels_of_checker(
                    warning, ClangTidy.ANALYZER_NAME))))

    return checker_info


def __print_profiles(args: argparse.Namespace, cl: CheckerLabels):
    """
    Print checker profiles according to the command line arguments to the
    standard output.
    """
    if args.output_format == 'custom':
        args.output_format = 'rows'

    if 'details' in args:
        header = ['Profile name', 'Description']
        rows = cl.get_description('profile').items()
    else:
        header = ['Profile name']
        rows = [(key,) for key in cl.get_description('profile')]

    if args.output_format in ['csv', 'json']:
        header = list(map(__uglify, header))

    print(twodim.to_str(args.output_format, header, rows))


def __print_severities(args: argparse.Namespace, cl: CheckerLabels):
    """
    Print checker severities according to the command line arguments to the
    standard output.
    """
    if args.output_format == 'custom':
        args.output_format = 'rows'

    if 'details' in args:
        header = ['Severity', 'Description']
        rows = cl.get_description('severity').items()
    else:
        header = ['Severity']
        rows = [(key,) for key in cl.get_description('severity')]

    if args.output_format in ['csv', 'json']:
        header = list(map(__uglify, header))

    print(twodim.to_str(args.output_format, header, rows))


def __print_guidelines(args: argparse.Namespace, cl: CheckerLabels):
    """
    Print guidelines according to the command line arguments to the standard
    output.
    """
    if args.output_format == 'custom':
        args.output_format = 'rows'

    result = {}

    for guideline in cl.get_description('guideline'):
        result[guideline] = set(cl.occurring_values(guideline))

    header = ['Guideline', 'Rules']
    if args.output_format in ['csv', 'json']:
        header = list(map(__uglify, header))

    if args.output_format == 'json':
        rows = [(g, sorted(list(r))) for g, r in result.items()]
    else:
        rows = [(g, ', '.join(sorted(r))) for g, r in result.items()]

    if args.output_format == 'rows':
        for row in rows:
            print('Guideline: {}'.format(row[0]))
            print('Rules: {}'.format(row[1]))
    else:
        print(twodim.to_str(args.output_format, header, rows))


def __print_labels(args: argparse.Namespace, cl: CheckerLabels):
    """
    Print labels according to the command line arguments to the standard
    output.
    """
    if args.output_format == 'custom':
        args.output_format = 'rows'

    header = ['Label']
    if args.output_format in ['csv', 'json']:
        header = list(map(__uglify, header))

    rows = list(map(lambda x: (x,), cl.labels()))

    print(twodim.to_str(args.output_format, header, rows))


def __print_label_values(args: argparse.Namespace, cl: CheckerLabels):
    """
    If --label flag is given an argument which doesn't contain a colon (:) then
    we assume that the user intends to see the available values of that label:
    CodeChecker checkers --label severity
    """
    if args.output_format == 'custom':
        args.output_format = 'rows'

    header = ['Value']
    if args.output_format == 'custom':
        args.output_format = 'rows'

    rows = list(map(lambda x: (x,), cl.occurring_values(args.label)))

    if rows:
        print(twodim.to_str(args.output_format, header, rows))
    else:
        LOG.info(
            'Label "%s" doesn\'t exist. Use "CodeChecker checkers --label" '
            'command to list available labels.', args.label)


def __format_row(row: Tuple) -> Tuple:
    """
    Perform some formatting of the detailed checker info.
    row -- A tuple with detailed checker info coming from
           __get_detailed_checker_info() function.
    """
    state = '+' if row[0] == CheckerState.enabled else \
        '-' if row[0] == CheckerState.disabled else \
        '?'

    labels = ', '.join(f'{k}:{v}' for k, v in row[4])

    return state, row[1], row[2], row[3], labels


def __print_checkers_custom_format(checkers: Iterable):
    """
    This function prints a detailed view of the selected checkers in a custom
    format. Due to its customness it isn't implemented in module twodim.
    """
    for checker in checkers:
        if checker[0] == CheckerState.enabled:
            status = 'enabled'
        elif checker[0] == CheckerState.disabled:
            status = 'disabled'
        else:
            status = 'unknown'

        print(checker[1])
        print('  Status:', status)
        print('  Analyzer:', checker[2])
        print('  Description:', checker[3])
        print('  Labels:')

        for label in checker[4]:
            print(f'    {label[0]}:{label[1]}')

        print()


def __print_checkers_json_format(checkers: Iterable, detailed: bool):
    """
    Print checker information in JSON format. This function is implemented to
    shorten __print_checkers(). JSON format is handled separately because its
    structure differs from other twodim formats.
    """
    def checker_info_dict(c):
        if c[0] == CheckerState.enabled:
            status = 'enabled'
        elif c[0] == CheckerState.disabled:
            status = 'disabled'
        else:
            status = 'unknown'

        return {
            'status': status,
            'name': c[1],
            'analyzer': c[2],
            'description': c[3],
            'labels': list(map(lambda x: f'{x[0]}:{x[1]}', c[4]))}

    if detailed:
        print(json.dumps([checker_info_dict(c) for c in checkers]))
    else:
        print(json.dumps([c[1] for c in checkers]))


def __post_process_result(result: List[Tuple]):
    """ Postprocess the given result.

    It will update the value of the doc_url label and create an absolute file
    path if it is a relative path.
    """
    data_files_dir_path = os.environ.get('CC_DATA_FILES_DIR', '')
    www_dir_path = os.path.join(data_files_dir_path, 'www')
    for res in result:
        for idx, (name, value) in enumerate(res[4]):
            if name == 'doc_url' and not value.startswith('http'):
                res[4][idx] = (name, os.path.normpath(
                    os.path.join(www_dir_path, value.strip(os.sep))))


def __print_checkers(args: argparse.Namespace, cl: CheckerLabels):
    """
    Print checkers according to the command line arguments to the standard
    output.
    """
    labels = [args.label] if 'label' in args else []

    if 'profile' in args:
        labels.append(f'profile:{args.profile}')

    if 'guideline' in args:
        labels.append(__guideline_to_label(args, cl))

    if 'severity' in args:
        labels.append(f'severity:{args.severity}')

    checker_info = __get_detailed_checker_info(args, cl)

    result = []
    for analyzer in args.analyzers:
        if labels:
            checkers = cl.checkers_by_labels(labels, analyzer)
            result.extend(
                filter(lambda x: x[1] in checkers, checker_info[analyzer]))
        else:
            result.extend(checker_info[analyzer])

    __post_process_result(result)

    if args.output_format == 'custom':
        if result:
            __print_checkers_custom_format(result)
        else:
            LOG.info('No checkers with the given label found.')
        return

    if args.output_format == 'json':
        __print_checkers_json_format(result, 'details' in args)
        return

    if 'details' in args:
        header = ['Status', 'Name', 'Analyzer', 'Description', 'Labels']
        rows = list(map(__format_row, result))
    else:
        header = ['Name']
        rows = [[r[1]] for r in result]

    if args.output_format in ['csv', 'json']:
        header = list(map(__uglify, header))

    if rows:
        print(twodim.to_str(args.output_format, header, rows))
    else:
        LOG.info('No checkers with the given label found.')


def __print_checker_config(args: argparse.Namespace):
    """
    Print checker config options according to the command line arguments to the
    standard output. The set of config options comes from the analyzers.
    """
    if args.output_format == 'custom':
        args.output_format = 'rows'

    context = analyzer_context.get_context()
    working_analyzers, errored = analyzer_types.check_supported_analyzers(
        args.analyzers,
        context)
    analyzer_types.check_available_analyzers(working_analyzers, errored)

    analyzer_environment = env.extend(context.path_env_extra,
                                      context.ld_lib_path_extra)

    analyzer_config_map = analyzer_types.build_config_handlers(
        args, context, working_analyzers)

    if 'details' in args:
        header = ['Option', 'Description']
    else:
        header = ['Option']

    if args.output_format in ['csv', 'json']:
        header = list(map(__uglify, header))

    rows = []
    analyzer_failures = []
    for analyzer in working_analyzers:
        config_handler = analyzer_config_map.get(analyzer)
        analyzer_class = analyzer_types.supported_analyzers[analyzer]

        configs = analyzer_class.get_checker_config(config_handler,
                                                    analyzer_environment)
        if not configs:
            # Checker configurations are not supported by cppcheck
            if analyzer != "cppcheck":
                analyzer_failures.append(analyzer)
                continue

        rows.extend((':'.join((analyzer, c[0])), c[1]) if 'details' in args
                    else (':'.join((analyzer, c[0])),) for c in configs)

    if rows:
        print(twodim.to_str(args.output_format, header, rows))

    analyzer_types.print_unsupported_analyzers(errored)

    if analyzer_failures:
        LOG.error("Failed to get checker configuration options for '%s' "
                  "analyzer(s)! Please try to upgrade your analyzer "
                  "version to use this feature.",
                  ', '.join(analyzer_failures))
        sys.exit(1)


def main(args):
    """
    List the checkers available in the specified (or all supported) analyzers
    alongside with their description or enabled status in various formats.
    """
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    logger.setup_logger(args.verbose if 'verbose' in args else None,
                        None if args.output_format == 'table' else 'stderr')

    cl = analyzer_context.get_context().checker_labels

    if 'profile' in args and not args.profile:
        __print_profiles(args, cl)
        return

    if 'severity' in args and not args.severity:
        __print_severities(args, cl)
        return

    if 'guideline' in args and not args.guideline:
        __print_guidelines(args, cl)
        return

    if 'label' in args and not args.label:
        __print_labels(args, cl)
        return

    if 'label' in args and ':' not in args.label:
        __print_label_values(args, cl)
        return

    if 'checker_config' in args:
        __print_checker_config(args)
        return

    __print_checkers(args, cl)
