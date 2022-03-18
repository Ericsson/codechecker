# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Calculates call statistics from analysis output
"""

from codechecker_common.logger import get_logger

from codechecker_statistics_collector.collectors.special_return_value import \
    SpecialReturnValueCollector
from codechecker_statistics_collector.collectors.return_value import \
    ReturnValueCollector

from .analyzer import ClangSA
from ..flag import has_flag
from ..flag import prepend_all

LOG = get_logger('analyzer')


def build_stat_coll_cmd(action, config, source):
    """
    Build the statistics collector analysis command.
    """

    cmd = [config.analyzer_binary, '-c', '-x', action.lang, '--analyze',
           # Do not warn about the unused gcc/g++ arguments.
           '-Qunused-arguments',
           '--analyzer-output', 'text']

    for plugin in config.analyzer_plugins:
        cmd.extend(["-Xclang", "-plugin",
                    "-Xclang", "checkercfg",
                    "-Xclang", "-load",
                    "-Xclang", plugin])

    cmd.extend(['-Xclang',
                '-analyzer-opt-analyze-headers'])

    cmd.extend(config.analyzer_extra_arguments)
    cmd.extend(action.analyzer_options)

    # Enable the statistics collector checkers only.
    collector_checkers = []
    checks = ClangSA.get_analyzer_checkers(config, config.environ, True, True)
    for checker_name, _ in checks:
        if SpecialReturnValueCollector.checker_collect in checker_name:
            collector_checkers.append(checker_name)

        if ReturnValueCollector.checker_collect in checker_name:
            collector_checkers.append(checker_name)

    if not collector_checkers:
        LOG.debug('No available statistics collector checkers were found')
        return [], False

    for coll_check in collector_checkers:
        cmd.extend(['-Xclang', f'-analyzer-checker={coll_check}'])

    compile_lang = action.lang
    if not has_flag('-x', cmd):
        cmd.extend(['-x', compile_lang])

    if not has_flag('--target', cmd) and action.target != "":
        cmd.append(f"--target={action.target}")

    if not has_flag('-std', cmd) and not has_flag('--std', cmd):
        cmd.append(action.compiler_standard)

    cmd.extend(prepend_all('-isystem', action.compiler_includes))

    if source:
        cmd.append(source)
    return cmd, True
