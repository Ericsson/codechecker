# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helpers for determining triple arch of a compile action
"""


from .. import analyzer_base
from ..flag import has_flag
from ..flag import prepend_all


def get_compile_command(action, config, source='', output=''):
    """ Generate a standardized and cleaned compile command serving as a base
    for other operations. """

    cmd = [config.analyzer_binary]

    if not has_flag('--target', cmd) and action.target != "":
        cmd.append(f"--target={action.target}")

    cmd.extend(prepend_all('-isystem', action.compiler_includes))
    cmd.append('-c')
    if not has_flag('-x', cmd):
        cmd.extend(['-x', action.lang])

    cmd.extend(config.analyzer_extra_arguments)
    cmd.extend(action.analyzer_options)
    if output:
        cmd.extend(['-o', output])
    if source:
        cmd.append(source)

    if not has_flag('-std', cmd) and not has_flag('--std', cmd):
        cmd.append(action.compiler_standard)
    return cmd


def _find_arch_in_command(output):
    # Sometimes this output can't be split by shlex.split(), because the
    # words of the command are surrounded with quotation mark thus it can
    # odd number of unescaped quotation marks in case the original command
    # included one. (By the way this crash happened at a user.)
    # Anyway the normal split() is enough for us because we just need to find
    # -triple flag and its parameter. These don't contain any special
    # characters that justifies the usage of shlex.split().
    res_cmd = [x.strip('"') for x in output.split()]

    try:
        arch = res_cmd[res_cmd.index('-triple') + 1]
        return arch.split('-')[0]
    except ValueError:
        pass


def get_triple_arch(action, source, config, env):
    """Returns the architecture part of the target triple for the given
    compilation command. """

    cmd = get_compile_command(action, config, source)
    cmd.insert(1, '-###')
    _, stdout, stderr = analyzer_base.SourceAnalyzer.run_proc(cmd,
                                                              env,
                                                              action.directory)

    # The -### flag in a Clang invocation emits the commands of substeps in a
    # build process (compilation phase, link phase, etc.). If there is -c flag
    # in the build command then there is no linking.
    return _find_arch_in_command(stdout + stderr) or ""
