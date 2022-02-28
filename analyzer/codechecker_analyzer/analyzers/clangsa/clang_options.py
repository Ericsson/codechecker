# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Clang Static analyzer version dependent arguments."""


import os

from codechecker_common.logger import get_logger

LOG = get_logger('analyzer')


def get_analyzer_checkers_cmd(cfg_handler, alpha=True, debug=False):
    """Return the checkers list getter command which depends on the used clang
    version.

    plugins -- A list of paths to clang plugins (so with checkers).

    Before clang9 alpha and debug checkers were printed by default.
    Since clang9 there are extra arguments to print the additional checkers.
    """
    command = [cfg_handler.analyzer_binary, "-cc1"]

    for plugin in cfg_handler.analyzer_plugins:
        command.extend(["-load", plugin])

    command.append("-analyzer-checker-help")

    # The clang compiler on OSX is a few
    # relases older than the open source clang release.
    # The new checker help printig flags are not available there yet.
    # If the OSX clang will be updated to based on clang v8
    # this early return can be removed.
    version_info = cfg_handler.version_info
    if not version_info or version_info.vendor != "clang":
        return command

    if alpha and version_info.major_version > 8:
        command.append("-analyzer-checker-help-alpha")

    if debug and version_info.major_version > 8:
        command.append("-analyzer-checker-help-developer")

    return command


def get_checker_config_cmd(cfg_handler, alpha=True, debug=True):
    """Return the checker config getter command which depends on the used clang
    version.
    """
    command = [cfg_handler.analyzer_binary, "-cc1"]

    for plugin in cfg_handler.analyzer_plugins:
        command.extend(["-load", plugin])

    command.append("-analyzer-checker-option-help")

    if cfg_handler.version_info.vendor != "clang":
        return command

    if alpha and cfg_handler.version_info.major_version > 8:
        command.append("-analyzer-checker-option-help-alpha")

    if debug and cfg_handler.version_info.major_version > 8:
        command.append("-analyzer-checker-option-help-developer")

    return command


def get_analyzer_config_cmd(cfg_handler):
    """Return the analyzer config getter command which depends on the used
    clang version.
    """
    command = [cfg_handler.analyzer_binary, "-cc1"]

    for plugin in cfg_handler.analyzer_plugins:
        command.extend(["-load", plugin])

    command.append("-analyzer-config-help")

    return command


def ctu_mapping(clang_version_info):
    """Clang version dependent ctu mapping tool path and mapping file name.

    The path of the mapping tool, which is assumed to be located
    inside the installed directory of the analyzer. Certain binary
    distributions can postfix the tool name with the major version
    number, the number and the tool name being separated by a dash. By
    default the shorter name is looked up, then if it is not found the
    postfixed.
    """
    if not clang_version_info:
        LOG.debug("No clang version information."
                  "Can not detect ctu mapping tool.")
        return None, None

    old_mapping_tool_name = 'clang-func-mapping'
    old_mapping_file_name = 'externalFnMap.txt'

    new_mapping_tool_name = 'clang-extdef-mapping'
    new_mapping_file_name = 'externalDefMap.txt'

    major_version = clang_version_info.major_version

    if major_version > 7:
        tool_name = new_mapping_tool_name
        mapping_file = new_mapping_file_name
    else:
        tool_name = old_mapping_tool_name
        mapping_file = old_mapping_file_name

    installed_dir = clang_version_info.installed_dir

    tool_path = os.path.join(installed_dir, tool_name)

    if os.path.isfile(tool_path):
        return tool_path, mapping_file

    LOG.debug(
        "Mapping tool '%s' suggested by autodetection is not found in "
        "directory reported by Clang '%s'. Trying with version-postfixed "
        "filename...", tool_path, installed_dir)

    postfixed_tool_path = ''.join([tool_path, '-', str(major_version)])

    if os.path.isfile(postfixed_tool_path):
        return postfixed_tool_path, mapping_file

    LOG.debug(
        "Postfixed mapping tool '%s' suggested by autodetection is not "
        "found in directory reported by Clang '%s'.",
        postfixed_tool_path, installed_dir)
    return None, None


def get_abos_options(clang_version_info):
    """ Get options to enable aggressive-binary-operation-simplification.

    Returns list of options which enables
    aggressive-binary-operation-simplification option (which is needed for the
    iterator checker) if the Clang version is greater then 8.
    Otherwise returns an empty list.
    """
    if clang_version_info and clang_version_info.major_version >= 8:
        return ['-Xclang',
                '-analyzer-config',
                '-Xclang',
                'aggressive-binary-operation-simplification=true']

    return []
