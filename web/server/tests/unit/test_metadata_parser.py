# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Unit tests for the metadata parser. """

import os
import unittest

from codechecker_server.metadata import MetadataInfoParser


metadata_cc_info = {
    'check_commands': [
        'CodeChecker.py analyze -o /path/to/reports /path/to/build.json'
    ],
    'analysis_duration': [1.0],
    'cc_version': '6.11 (930440d6a6cae80f615146547f4b169c7629d558)',
    'analyzer_statistics': {
        'clangsa': {
            'successful': 1,
            'failed': 0,
            'version': 'clang version 7.0.0',
            'failed_sources': []
        },
        'clang-tidy': {
            'successful': 10,
            'failed': 0,
            'version': 'LLVM version 7.0.0',
            'failed_sources': []
        }
    },
    'checkers': {
        'clangsa': {
            'alpha.clone.CloneChecker': False,
            'deadcode.DeadStores': True
        },
        'clang-tidy': {
            'bugprone-use-after-move': True,
            'abseil-string-find-startswith': False
        }
    }
}

metadata_multiple_info = {
    'check_commands': [
        'CodeChecker.py analyze -o /path/to/reports /path/to/build.json',
        'cppcheck /path/to/main.cpp'
    ],
    'analysis_duration': [1.0, 1.0],
    'cc_version': '6.11 (930440d6a6cae80f615146547f4b169c7629d558)',
    'analyzer_statistics': {
        'clangsa': {
            'successful': 1,
            'failed': 0,
            'version': 'clang version 7.0.0',
            'failed_sources': []
        },
        'clang-tidy': {
            'successful': 10,
            'failed': 0,
            'version': 'LLVM version 7.0.0',
            'failed_sources': []
        },
        'cppcheck': {
            "failed": 0,
            "failed_sources": [],
            "successful": 1,
            "version": "Cppcheck 1.87"
        }
    },
    'checkers': {
        'clangsa': {
            'alpha.clone.CloneChecker': False,
            'deadcode.DeadStores': True
        },
        'clang-tidy': {
            'bugprone-use-after-move': True,
            'abseil-string-find-startswith': False
        },
        'cppcheck': {}
    }
}


metadata_mult_cppcheck_info = {
    'check_commands': [
        'cppcheck /path/to/main.cpp',
        'cppcheck -I /path/to/include /path/to/main.cpp'
    ],
    'analysis_duration': [1.0, 1.0],
    'cc_version': None,
    'analyzer_statistics': {
        'cppcheck': {
            "failed": 0,
            "failed_sources": [],
            "successful": 2,
            "version": "Cppcheck 1.87"
        }
    },
    'checkers': {
        'cppcheck': {}
    }
}


class MetadataInfoParserTest(unittest.TestCase):
    """ Testing metadata parser. """

    @classmethod
    def setup_class(self):
        """ Initialize test files. """
        # Already generated plist files for the tests.
        self.__metadata_test_files = os.path.join(
            os.path.dirname(__file__), 'metadata_test_files')

    def test_metadata_info_v1(self):
        """ Get metadata info for old version format json file. """
        metadata_v1 = os.path.join(self.__metadata_test_files, 'v1.json')
        mip = MetadataInfoParser(metadata_v1)

        self.assertEqual(len(mip.check_commands), 1)
        self.assertEqual(' '.join(metadata_cc_info['check_commands']),
                         mip.check_commands[0])

        self.assertEqual(metadata_cc_info['analysis_duration'][0],
                         mip.check_durations[0])

        self.assertEqual(metadata_cc_info['cc_version'], mip.cc_version)

        self.assertDictEqual(metadata_cc_info['analyzer_statistics'],
                             mip.analyzer_statistics)

        self.assertDictEqual(metadata_cc_info['checkers'],
                             mip.checkers)

    def test_metadata_info_v2(self):
        """ Get metadata info for new version format json. """
        metadata_v2 = os.path.join(self.__metadata_test_files, 'v2.json')
        mip = MetadataInfoParser(metadata_v2)

        self.assertEqual(len(mip.check_commands), 1)
        self.assertEqual(' '.join(metadata_cc_info['check_commands']),
                         list(mip.check_commands)[0])

        self.assertEqual(metadata_cc_info['analysis_duration'][0],
                         mip.check_durations[0])

        self.assertEqual(metadata_cc_info['cc_version'], mip.cc_version)

        self.assertDictEqual(metadata_cc_info['analyzer_statistics'],
                             mip.analyzer_statistics)

        self.assertDictEqual(metadata_cc_info['checkers'],
                             mip.checkers)

    def test_multiple_metadata_info(self):
        """ Get metadata info from multiple analyzers. """
        metadata_multiple = os.path.join(
            self.__metadata_test_files, 'v2_multiple.json')
        mip = MetadataInfoParser(metadata_multiple)

        self.assertEqual(len(mip.check_commands), 2)
        for command in metadata_multiple_info['check_commands']:
            self.assertTrue(command in mip.check_commands)

        self.assertEqual(int(sum(metadata_multiple_info['analysis_duration'])),
                         int(sum(mip.check_durations)))

        self.assertEqual(metadata_multiple_info['cc_version'], mip.cc_version)

        self.assertDictEqual(metadata_multiple_info['analyzer_statistics'],
                             mip.analyzer_statistics)

        self.assertDictEqual(mip.checkers, {})

    def test_multiple_cppcheck_metadata_info(self):
        """ Get metadata info from multiple cppcheck analyzers. """
        metadata_multiple = os.path.join(
            self.__metadata_test_files, 'v2_multiple_cppcheck.json')
        mip = MetadataInfoParser(metadata_multiple)

        self.assertEqual(len(mip.check_commands), 2)
        for command in metadata_mult_cppcheck_info['check_commands']:
            self.assertTrue(command in mip.check_commands)

        self.assertEqual(
            int(sum(metadata_mult_cppcheck_info['analysis_duration'])),
            int(sum(mip.check_durations)))

        self.assertEqual(
            metadata_mult_cppcheck_info['cc_version'], mip.cc_version)

        expected_stats = metadata_mult_cppcheck_info['analyzer_statistics']
        expected_cppcheck_stats = expected_stats['cppcheck']
        cppcheck_stats = mip.analyzer_statistics['cppcheck']

        self.assertEqual(expected_cppcheck_stats['failed'],
                         cppcheck_stats['failed'])

        self.assertEqual(len(expected_cppcheck_stats['failed_sources']),
                         len(cppcheck_stats['failed_sources']))

        self.assertEqual(expected_cppcheck_stats['successful'],
                         cppcheck_stats['successful'])

        self.assertDictEqual(mip.checkers, {})
