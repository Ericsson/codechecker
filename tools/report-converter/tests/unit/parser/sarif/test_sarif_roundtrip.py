# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test that converting reports to sarif and parsing them back is lossless.
"""


import glob
import json
import os
import shutil
import tempfile
import unittest

from codechecker_report_converter.report import BugPathEvent, \
    BugPathPosition, File, MacroExpansion, Range, Report, report_file
from codechecker_report_converter.report.hash import get_report_hash, \
    HashType
from codechecker_report_converter.report.parser import sarif
from codechecker_report_converter.report.parser.base import AnalyzerInfo


PLIST_TEST_FILES_DIR = os.path.join(
    os.path.dirname(__file__), os.pardir, 'plist', 'plist_test_files')


def report_to_dict(report: Report) -> dict:
    """ All data of a report which must survive a round trip. """
    data = report.to_json()
    del data["analyzer_result_file_path"]
    del data["review_status"]
    return data


def create_full_report(
    file_path: str = '/home/user/project/src/main.c',
    analyzer_name: str | None = 'clangsa',
    checker_name: str = 'core.NullDereference',
    report_hash: str | None = '3f7c2b9e1d4a5f6b8c0e2d4f6a8b0c1d'
) -> Report:
    """ Create a report which uses every field of the report model. """
    main = File(file_path)
    header = File(os.path.join(os.path.dirname(file_path), 'util.h'))

    return Report(
        file=main, line=12, column=6,
        message="Dereference of null pointer (loaded from variable 'p')",
        checker_name=checker_name,
        severity='HIGH',
        report_hash=report_hash,
        analyzer_name=analyzer_name,
        category='Logic error',
        type='clangsa',
        bug_path_events=[
            # Position differs from the start of the range.
            BugPathEvent("'p' initialized to a null pointer value",
                         header, 10, 3, Range(10, 12, 10, 14)),
            # Event without range.
            BugPathEvent("Calling 'foo'", main, 11, 3),
            BugPathEvent(
                "Dereference of null pointer (loaded from variable 'p')",
                main, 12, 6, Range(12, 6, 12, 6))],
        bug_path_positions=[
            BugPathPosition(header, Range(10, 3, 10, 5)),
            BugPathPosition(main, Range(12, 3, 12, 8)),
            BugPathPosition(main, None)],
        notes=[BugPathEvent("note here", header, 4, 1, Range(4, 1, 4, 9)),
               BugPathEvent("note without range", main, 5, 2)],
        macro_expansions=[MacroExpansion(
            "((void *)0)", "NULL", header, 10, 12)],
        annotations={'timestamp': '2000-01-01 12:00', 'chronological_order':
                     '42'})


class SarifRoundTripTestCase(unittest.TestCase):
    """ Report -> sarif -> Report must not lose any information. """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def __round_trip(
        self,
        reports: list[Report],
        source_dir_path: str | None = None
    ) -> list[Report]:
        out = os.path.join(self.tmp_dir, 'reports.sarif')
        parser = sarif.Parser()
        parser.write(parser.convert(reports), out)
        return sarif.Parser().get_reports(out, source_dir_path)

    def __assert_same(self, orig: list[Report], new: list[Report]):
        self.assertEqual(len(orig), len(new))
        for o, n in zip(orig, new):
            self.assertEqual(report_to_dict(o), report_to_dict(n))

    def test_plist_test_files(self):
        """ Every plist test file survives the round trip. """
        plist_files = glob.glob(os.path.join(PLIST_TEST_FILES_DIR, '*.plist'))
        self.assertTrue(plist_files)

        for plist_file in plist_files:
            orig = report_file.get_reports(plist_file)
            for report in orig:
                self.assertIsNotNone(report.report_hash)

            new = self.__round_trip(orig)
            # Group order (one run per analyzer) is the same for one analyzer.
            self.__assert_same(orig, new)

    def test_full_report(self):
        """ All fields of the report model survive the round trip. """
        orig = [create_full_report()]
        self.__assert_same(orig, self.__round_trip(orig))

    def test_full_report_via_plist(self):
        """ plist -> sarif contains everything which was in the plist. """
        plist_path = os.path.join(self.tmp_dir, 'x.plist')
        report_file.create(plist_path, [create_full_report()],
                           analyzer_info=AnalyzerInfo('clangsa'))
        orig = report_file.get_reports(plist_path)
        self.__assert_same(orig, self.__round_trip(orig))

    def test_hash_not_recomputed(self):
        """
        The hash is copied verbatim and not recomputed even if the source
        file is not available.
        """
        report = create_full_report(
            file_path='/nonexistent/dir/main.c', report_hash='deadbeef')
        new = self.__round_trip([report])
        self.assertEqual(new[0].report_hash, 'deadbeef')

        out = os.path.join(self.tmp_dir, 'reports.sarif')
        with open(out, encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(
            data['runs'][0]['results'][0]['partialFingerprints'],
            {sarif.REPORT_HASH_KEY: 'deadbeef'})

    def test_missing_hash_is_computed_when_reading(self):
        """ The writer never invents a hash. """
        report = create_full_report(report_hash=None)
        data = sarif.Parser().convert([report])
        self.assertNotIn(
            'partialFingerprints', data['runs'][0]['results'][0])

    def test_one_run_per_analyzer(self):
        """ A separate run is created for each analyzer. """
        reports = [
            create_full_report(analyzer_name='clangsa'),
            create_full_report(analyzer_name='clang-tidy',
                               checker_name='bugprone-use-after-move',
                               report_hash='1'),
            create_full_report(analyzer_name='clangsa',
                               checker_name='core.DivideZero',
                               report_hash='2'),
            create_full_report(analyzer_name=None, checker_name='x',
                               report_hash='3')]

        data = sarif.Parser().convert(reports)
        runs = data['runs']
        self.assertEqual([r['tool']['driver']['name'] for r in runs],
                         ['clang-tidy', 'clangsa', 'unknown'])
        self.assertEqual(
            [[res['ruleId'] for res in r['results']] for r in runs],
            [['bugprone-use-after-move'],
             ['core.NullDereference', 'core.DivideZero'],
             ['x']])
        for run in runs:
            driver = run['tool']['driver']
            self.assertIn('generatedBy', driver['properties'])
            for res in run['results']:
                self.assertEqual(
                    driver['rules'][res['ruleIndex']]['id'], res['ruleId'])

        new = self.__round_trip(reports)
        self.assertEqual(
            sorted((r.analyzer_name or '', r.checker_name) for r in new),
            sorted((r.analyzer_name or '', r.checker_name) for r in reports))

    def test_special_characters_in_path(self):
        """ File paths are percent-encoded in URIs. """
        path = '/home/user/my proj/100%/#ñoñ_äscïï.c'
        report = create_full_report(file_path=path)
        data = sarif.Parser().convert([report])
        uri = data['runs'][0]['results'][0]['locations'][0][
            'physicalLocation']['artifactLocation']['uri']
        self.assertNotIn(' ', uri)
        self.assertNotIn('#', uri)

        new = self.__round_trip([report])
        self.assertEqual(new[0].file.path, path)
        self.__assert_same([report], new)

    def test_trim_path_prefix(self):
        """ Trimmed paths are written as relative references. """
        report = create_full_report()
        report.trim_path_prefixes(['/home/user/project'])

        new = self.__round_trip([report])
        self.assertEqual(new[0].file.path, 'src/main.c')
        self.assertEqual(new[0].report_hash, report.report_hash)

        new = self.__round_trip([report], source_dir_path='/root')
        self.assertEqual(new[0].file.path, '/root/src/main.c')

    def test_empty(self):
        """ No reports result in a valid sarif file without runs. """
        data = sarif.Parser().convert([])
        self.assertEqual(data['runs'], [])
        self.assertEqual(self.__round_trip([]), [])

    def test_malformed_file(self):
        """ Malformed sarif files do not crash the parser. """
        out = os.path.join(self.tmp_dir, 'bad.sarif')
        for content in ['{', '[]', '{"runs": null}',
                        '{"runs": [{"results": [{"ruleId": "x"}]}]}']:
            with open(out, 'w', encoding='utf-8') as f:
                f.write(content)
            self.assertEqual(sarif.Parser().get_reports(out), [])

    def test_replace_report_hash(self):
        """ Report hashes can be replaced in sarif files. """
        src_dir = os.path.join(PLIST_TEST_FILES_DIR, 'gen_plist')
        reports = report_file.get_reports(
            os.path.join(PLIST_TEST_FILES_DIR, 'clang-4.0.plist'))
        out = os.path.join(self.tmp_dir, 'reports.sarif')
        report_file.create(out, reports)

        report_file.replace_report_hash(out, HashType.CONTEXT_FREE)

        new = report_file.get_reports(out)
        self.assertTrue(os.path.isdir(src_dir))
        self.assertEqual(
            [r.report_hash for r in new],
            [get_report_hash(r, HashType.CONTEXT_FREE) for r in reports])
