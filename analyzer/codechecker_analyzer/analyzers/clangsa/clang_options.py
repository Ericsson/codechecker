# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""Clang Static analyzer version dependent arguments."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os


def get_analyzer_checkers_cmd(clang_version_info, env, plugins,
                              alpha=True, debug=True):
    """Return the checkers list which depends on the used clang version.

    plugins should be a list of path to clang plugins (so with checkers)

    Before clang9 alpha and debug checkers were printed by default.
    Since clang9 there are extra arguments to print the additional checkers.
    """
    major_version = clang_version_info.major_version
    command = []

    for plugin in plugins:
        command.extend(["-load", plugin])

    command.append("-analyzer-checker-help")

    if alpha and major_version > 8:
        command.append("-analyzer-checker-help-alpha")

    if debug and major_version > 8:
        command.append("-analyzer-checker-help-developer")

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
