# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helpers to parse metadata.json file.
"""

from abc import ABCMeta
import os


from codechecker_common.logger import get_logger
from codechecker_common.util import load_json_or_empty

LOG = get_logger('system')


class MetadataInfoParser(object):
    """ Metadata info parser. """

    __metaclass__ = ABCMeta

    def __get_metadata_info_v1(self, metadata_dict):
        """ Get metadata information from the old version json file. """
        check_commands = []
        check_durations = []
        cc_version = None
        analyzer_statistics = {}
        checkers = {}

        if 'command' in metadata_dict:
            check_commands.append(metadata_dict['command'])
        if 'timestamps' in metadata_dict:
            check_durations.append(
                float(metadata_dict['timestamps']['end'] -
                      metadata_dict['timestamps']['begin']))

        # Get CodeChecker version.
        cc_version = metadata_dict.get('versions', {}).get('codechecker')

        # Get analyzer statistics.
        analyzer_statistics = metadata_dict.get('analyzer_statistics', {})

        # Get analyzer checkers.
        checkers = metadata_dict.get('checkers', {})

        return check_commands, check_durations, cc_version, \
            analyzer_statistics, checkers

    def __insert_analyzer_statistics(self, source, dest, analyzer_name):
        """ Insert stats from source to dest of the given analyzer. """
        if not source:
            return

        if analyzer_name in dest:
            dest[analyzer_name]['failed'] += source['failed']
            dest[analyzer_name]['failed_sources'].extend(
                source['failed_sources'])
            dest[analyzer_name]['successful'] += source['successful']
            dest[analyzer_name]['version'].update([source['version']])
        else:
            dest[analyzer_name] = source
            dest[analyzer_name]['version'] = set([source['version']])

    def __insert_checkers(self, source, dest, analyzer_name):
        """ Insert checkers from source to dest of the given analyzer. """
        if analyzer_name in dest:
            d_chks = dest[analyzer_name]
            for checker in source:
                if checker in d_chks and source[checker] != d_chks[checker]:
                    LOG.warning('Different checker statuses for %s', checker)
                dest[analyzer_name][checker] = source[checker]
        else:
            dest[analyzer_name] = source

    def __get_metadata_info_v2(self, metadata_dict):
        """ Get metadata information from the new version format json file. """
        cc_version = []
        check_commands = []
        check_durations = []
        analyzer_statistics = {}
        checkers = {}

        tools = metadata_dict.get('tools', {})
        for tool in tools:
            if tool['name'] == 'codechecker' and 'version' in tool:
                cc_version.append(tool['version'])

            if 'command' in tool:
                check_commands.append(tool['command'])

            if 'timestamps' in tool:
                check_durations.append(
                    float(tool['timestamps']['end'] -
                          tool['timestamps']['begin']))

            if 'analyzers' in tool:
                for analyzer_name, analyzer_info in tool['analyzers'].items():
                    self.__insert_analyzer_statistics(
                        analyzer_info.get('analyzer_statistics', {}),
                        analyzer_statistics,
                        analyzer_name)

                    self.__insert_checkers(
                        analyzer_info.get('checkers', {}),
                        checkers,
                        analyzer_name)
            else:
                self.__insert_analyzer_statistics(
                    tool.get('analyzer_statistics', {}),
                    analyzer_statistics,
                    tool['name'])

                self.__insert_checkers(tool.get('checkers', {}),
                                       checkers,
                                       tool['name'])

        # FIXME: if multiple report directories are stored created by different
        # codechecker versions there can be multiple results with OFF detection
        # status. If additional reports are stored created with cppcheck all
        # the cppcheck analyzer results will be marked with unavailable
        # detection status. To solve this problem we will return with an empty
        # checker set. This way detection statuses will be calculated properly
        # but OFF and UNAVAILABLE checker statuses will never be used.
        num_of_report_dir = metadata_dict.get('num_of_report_dir')
        if num_of_report_dir > 1:
            checkers = {}

        cc_version = '; '.join(cc_version) if cc_version else None

        for analyzer in analyzer_statistics:
            analyzer_statistics[analyzer]['version'] = \
                '; '.join(analyzer_statistics[analyzer]['version'])

        return check_commands, check_durations, cc_version, \
            analyzer_statistics, checkers

    def get_metadata_info(self, metadata_file):
        """ Get metadata information from the given file. """
        if not os.path.isfile(metadata_file):
            return [], [], None, {}, {}

        metadata_dict = load_json_or_empty(metadata_file, {})

        if 'version' in metadata_dict:
            return self.__get_metadata_info_v2(metadata_dict)
        else:
            return self.__get_metadata_info_v1(metadata_dict)
