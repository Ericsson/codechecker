# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helpers to manage metadata.json file.
"""

from codechecker_report_converter.util import load_json_or_empty

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def metadata_v1_to_v2(metadata_dict):
    """ Convert old version metadata to a new version format. """

    if 'version' in metadata_dict and metadata_dict['version'] >= 2:
        return metadata_dict

    ret = {'version': 2, 'tools': []}
    tool = {
        'name': 'codechecker',
        'version': metadata_dict.get('versions', {}).get('codechecker'),
        'command': metadata_dict.get('command'),
        'output_path': metadata_dict.get('output_path'),
        'skipped': metadata_dict.get('skipped'),
        'timestamps': metadata_dict.get('timestamps'),
        'working_directory': metadata_dict.get('working_directory'),
        'analyzers': {},
        'result_source_files': metadata_dict.get('result_source_files')}

    for analyzer_name in sorted(metadata_dict['checkers'].keys()):
        checkers = metadata_dict['checkers'][analyzer_name]
        if not isinstance(checkers, dict):
            checkers = {checker_name: True for checker_name in checkers}

        analyzer_stats = metadata_dict.get('analyzer_statistics', {})

        tool['analyzers'][analyzer_name] = {
            'checkers': checkers,
            'analyzer_statistics': analyzer_stats.get(analyzer_name, {})}

    ret["tools"].append(tool)

    return ret


def merge_metadata_json(metadata_files, num_of_report_dir=1):
    """ Merge content of multiple metadata files and return it as json. """

    if not metadata_files:
        return {}

    ret = {
        'version': 2,
        'num_of_report_dir': num_of_report_dir,
        'tools': []}

    for metadata_file in metadata_files:
        try:
            metadata_dict = load_json_or_empty(metadata_file, {})
            metadata = metadata_v1_to_v2(metadata_dict)
            for tool in metadata['tools']:
                ret['tools'].append(tool)
        except Exception as ex:
            LOG.warning('Failed to parse %s file with the following error: %s',
                        metadata_file, str(ex))

    return ret
