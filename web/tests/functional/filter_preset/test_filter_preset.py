# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Functional tests for filter preset Thrift API.
"""

import os
import unittest

from codechecker_api.codeCheckerDBAccess_v6 import ttypes

from codechecker_api_shared.ttypes import RequestFailed

from libtest import env

from . import setup_class, teardown_class


class TestFilterPresetAPI(unittest.TestCase):
    """
    Test filter preset Thrift API methods:
    - storeFilterPreset
    - getFilterPreset
    - listFilterPreset
    - deleteFilterPreset
    """

    def setup_class(self):
        """
        Setup the environment for testing filter_preset.
        """
        setup_class()

    def teardown_class(self):
        """
        Clean up after the test.
        """
        teardown_class()

    def setup_method(self, _):
        """
        Setup before each test method.
        """
        self._test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print(f'Running {test_class} tests in {self._test_workspace}')

        self._cc_client = env.setup_viewer_client(self._test_workspace)
        self.assertIsNotNone(self._cc_client)

    def teardown_method(self, _):
        """
        Clean up after each test method.
        """
        presets = self._cc_client.listFilterPreset()
        for preset in presets:
            self._cc_client.deleteFilterPreset(preset.id)

    # ========== storeFilterPreset Tests ==========

    def test_store_filter_preset_creates_new(self):
        """
        Test storeFilterPreset creates a new preset.
        """
        report_filter = ttypes.ReportFilter(
            severity=[50, 40],  # CRITICAL, HIGH
            checkerName=['clang*']
        )

        preset = ttypes.FilterPreset(
            id=-1,
            name="TestPreset",
            reportFilter=report_filter
        )

        preset_id = self._cc_client.storeFilterPreset(preset)

        self.assertEqual(preset_id, 1, "Should return valid ID")

    def test_store_filter_preset_updates_existing(self):
        """
        Test storeFilterPreset updates an existing preset with same name.
        """
        preset_name = "UpdateTest"

        report_filter = ttypes.ReportFilter(severity=[50])
        preset = ttypes.FilterPreset(
            -1,
            preset_name,
            report_filter
            )

        preset_id = self._cc_client.storeFilterPreset(preset)
        self.assertEqual(preset_id, 1)

        updated_filter = ttypes.ReportFilter(severity=[50, 40, 30])
        updated_preset = ttypes.FilterPreset(1,
                                             preset_name,
                                             updated_filter)

        new_id = self._cc_client.storeFilterPreset(updated_preset)
        self.assertEqual(new_id, 1)

        all_presets = self._cc_client.listFilterPreset()
        preset_names = [p.name for p in all_presets]

        self.assertEqual(preset_names.count(preset_name), 1)

        stored = self._cc_client.getFilterPreset(new_id)
        self.assertEqual(len(stored.reportFilter.severity), 3)

    def test_store_filter_preset_with_complex_filter(self):
        """
        Test storeFilterPreset with complex ReportFilter.
        """
        report_filter = ttypes.ReportFilter(
            severity=[50, 40, 30],
            checkerName=['clang-tidy*', 'clangsa*'],
            filepath=['*/src/*', '*/include/*'],
            checkerMsg=['*memory*'],
            reviewStatus=[0, 1],  # UNREVIEWED, CONFIRMED
            detectionStatus=[0, 3],  # NEW, REOPENED
            bugPathLength=ttypes.BugPathLengthRange(min=10, max=50),
            isUnique=True,
            componentNames=['component1'],
            analyzerNames=['clangsa', 'clang-tidy']
        )

        preset = ttypes.FilterPreset(-1, "ComplexPreset", report_filter)

        preset_id = self._cc_client.storeFilterPreset(preset)

        self.assertNotEqual(preset_id, -1)
        self.assertEqual(preset_id, 1)

    def test_store_filter_preset_with_empty_filter(self):
        """
        Test storeFilterPreset with empty ReportFilter.
        """
        report_filter = ttypes.ReportFilter()
        preset = ttypes.FilterPreset(-1, "EmptyFilter", report_filter)

        preset_id = self._cc_client.storeFilterPreset(preset)

        self.assertNotEqual(preset_id, -1)
        self.assertEqual(preset_id, 1)

        stored = self._cc_client.getFilterPreset(preset_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.name, "EmptyFilter")
        self.assertIsNotNone(stored.reportFilter)
        self.assertEqual(stored.reportFilter.filepath, None)
        self.assertEqual(stored.reportFilter.checkerMsg, None)
        self.assertEqual(stored.reportFilter.checkerName, None)
        self.assertEqual(stored.reportFilter.reportHash, None)
        self.assertEqual(stored.reportFilter.severity, None)
        self.assertEqual(stored.reportFilter.reviewStatus, None)
        self.assertEqual(stored.reportFilter.detectionStatus, None)
        self.assertEqual(stored.reportFilter.runHistoryTag, None)
        self.assertEqual(stored.reportFilter.firstDetectionDate, None)
        self.assertEqual(stored.reportFilter.fixDate, None)
        self.assertEqual(stored.reportFilter.isUnique, None)
        self.assertEqual(stored.reportFilter.runName, None)
        self.assertEqual(stored.reportFilter.runTag, None)
        self.assertEqual(stored.reportFilter.componentNames, None)
        self.assertEqual(stored.reportFilter.bugPathLength, None)
        self.assertEqual(stored.reportFilter.date, None)
        self.assertEqual(stored.reportFilter.analyzerNames, None)
        self.assertEqual(stored.reportFilter.openReportsDate, None)
        self.assertEqual(stored.reportFilter.cleanupPlanNames, None)
        self.assertEqual(stored.reportFilter.fileMatchesAnyPoint, None)
        self.assertEqual(stored.reportFilter.componentMatchesAnyPoint, None)
        self.assertEqual(stored.reportFilter.annotations, [])
        self.assertEqual(stored.reportFilter.reportStatus, None)

    def test_store_filter_preset_returns_error(self):
        """
        Test storeFilterPreset returns error on empty preset name
        and attempt to store None.
        """

        preset = ttypes.FilterPreset(None,
                                     None,
                                     ttypes.ReportFilter())

        with self.assertRaises(RequestFailed):
            self._cc_client.storeFilterPreset(preset)

        with self.assertRaises(RequestFailed):
            self._cc_client.storeFilterPreset(None)

    # ========== getFilterPreset Tests ==========

    def test_get_filter_preset_by_id(self):
        """
        Test getFilterPreset retrieves preset by ID.
        """

        report_filter = ttypes.ReportFilter(
            severity=[50],
            checkerName=['clang-tidy*'],
            reviewStatus=[0, 1]
        )
        preset = ttypes.FilterPreset(-1,
                                     "GetTest",
                                     report_filter)

        preset_id = self._cc_client.storeFilterPreset(preset)

        stored_preset = self._cc_client.getFilterPreset(preset_id)

        self.assertIsNotNone(stored_preset)
        self.assertEqual(stored_preset.id, preset_id)
        self.assertEqual(stored_preset.name, "GetTest")
        self.assertIsNotNone(stored_preset.reportFilter)
        self.assertEqual(stored_preset.reportFilter.severity, [50])
        self.assertEqual(stored_preset.reportFilter.checkerName,
                         ['clang-tidy*'])
        self.assertEqual(stored_preset.reportFilter.reviewStatus, [0, 1])

    def test_get_filter_preset_returns_error_for_nonexistent(self):
        """
        Test getFilterPreset returns RequestFailed for non-existent ID.
        """
        with self.assertRaises(RequestFailed):
            self._cc_client.getFilterPreset(999)

    def test_get_filter_preset_preserves_all_fields(self):
        """
        Test getFilterPreset preserves all ReportFilter fields.
        """

        report_filter = ttypes.ReportFilter(
            severity=[50, 40],
            checkerName=['check1*', 'check2*'],
            filepath=['*/path1/*', '*/path2/*'],
            checkerMsg=['*msg*'],
            reviewStatus=[0, 1, 2],
            detectionStatus=[0, 3],
            reportHash=['hash1', 'hash2'],
            bugPathLength=ttypes.BugPathLengthRange(min=5, max=20),
            isUnique=True,
            componentNames=['comp1', 'comp2'],
            analyzerNames=['clangsa']
        )
        preset = ttypes.FilterPreset(-1,
                                     "CompleteTest",
                                     report_filter)

        preset_id = self._cc_client.storeFilterPreset(preset)

        self.assertEqual(preset_id, 1)

        stored = self._cc_client.getFilterPreset(preset_id)

        rf = stored.reportFilter

        self.assertEqual(len(rf.severity), 2)
        self.assertEqual(len(rf.checkerName), 2)
        self.assertEqual(len(rf.filepath), 2)
        self.assertEqual(len(rf.checkerMsg), 1)
        self.assertEqual(len(rf.reviewStatus), 3)
        self.assertEqual(len(rf.detectionStatus), 2)
        self.assertEqual(len(rf.reportHash), 2)
        self.assertEqual(rf.bugPathLength.min, 5)
        self.assertEqual(rf.bugPathLength.max, 20)
        self.assertTrue(rf.isUnique)
        self.assertEqual(len(rf.componentNames), 2)
        self.assertEqual(len(rf.analyzerNames), 1)

    # ========== listFilterPreset Tests ==========

    def test_list_filter_preset_empty(self):
        """
        Test listFilterPreset returns empty list when no presets exist.
        """

        presets = self._cc_client.listFilterPreset()

        self.assertIsNotNone(presets)
        self.assertIsInstance(presets, list)
        self.assertEqual(len(presets), 0)

    def test_list_filter_preset_single(self):
        """
        Test listFilterPreset returns single preset.
        """

        preset = ttypes.FilterPreset(-1,
                                     "SinglePreset",
                                     ttypes.ReportFilter(severity=[50]))

        preset_id = self._cc_client.storeFilterPreset(preset)

        presets = self._cc_client.listFilterPreset()

        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0].id, preset_id)
        self.assertEqual(presets[0].name, "SinglePreset")

    def test_list_filter_preset_multiple(self):
        """
        Test listFilterPreset returns all presets.
        """

        preset1 = ttypes.FilterPreset(-1,
                                      "Preset1",
                                      ttypes.ReportFilter(severity=[50]))
        preset2 = ttypes.FilterPreset(-1,
                                      "Preset2",
                                      ttypes.ReportFilter(severity=[40]))
        preset3 = ttypes.FilterPreset(-1,
                                      "Preset3",
                                      ttypes.ReportFilter(severity=[30]))

        id1 = self._cc_client.storeFilterPreset(preset1)
        id2 = self._cc_client.storeFilterPreset(preset2)
        id3 = self._cc_client.storeFilterPreset(preset3)

        presets = self._cc_client.listFilterPreset()

        self.assertEqual(len(presets), 3)

        preset_ids = [p.id for p in presets]
        # check if id's of all three presets are in the list
        # of returned presets.
        self.assertIn(id1, preset_ids)
        self.assertIn(id2, preset_ids)
        self.assertIn(id3, preset_ids)

        # check that the id's are correct.
        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)
        self.assertEqual(id3, 3)

        # check that the names are in the list of returned presets.
        preset_names = [p.name for p in presets]
        self.assertIn("Preset1", preset_names)
        self.assertIn("Preset2", preset_names)
        self.assertIn("Preset3", preset_names)

    def test_list_filter_preset_includes_report_filter(self):
        """
        Test listFilterPreset includes full ReportFilter for each preset.
        """
        report_filter_1 = ttypes.ReportFilter(severity=[50],
                                              checkerName=['clang*'])
        report_filter_2 = ttypes.ReportFilter(reviewStatus=[0, 1])

        preset1 = ttypes.FilterPreset(-1,
                                      "WithFilter1",
                                      report_filter_1)

        preset2 = ttypes.FilterPreset(-1,
                                      "WithFilter2",
                                      report_filter_2)

        id1 = self._cc_client.storeFilterPreset(preset1)
        id2 = self._cc_client.storeFilterPreset(preset2)

        self.assertNotEqual(id1, -1)
        self.assertNotEqual(id2, -1)

        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)

        presets = self._cc_client.listFilterPreset()

        for preset in presets:
            self.assertIsNotNone(preset.reportFilter)
            if preset.name == "WithFilter1":
                self.assertEqual(preset.reportFilter.severity, [50])
                self.assertEqual(preset.reportFilter.checkerName, ['clang*'])
            elif preset.name == "WithFilter2":
                self.assertEqual(preset.reportFilter.reviewStatus, [0, 1])

    # ========== deleteFilterPreset Tests ==========

    def test_delete_filter_preset_removes_preset(self):
        """
        Test deleteFilterPreset removes the preset.
        """

        preset = ttypes.FilterPreset(-1,
                                     "DeleteTest",
                                     ttypes.ReportFilter(severity=[50]))

        preset_id = self._cc_client.storeFilterPreset(preset)

        all_presets = self._cc_client.listFilterPreset()
        self.assertEqual(len(all_presets), 1)

        deleted_preset_id = self._cc_client.deleteFilterPreset(preset_id)

        self.assertNotEqual(deleted_preset_id, -1)
        self.assertEqual(deleted_preset_id, preset_id)

        all_presets = self._cc_client.listFilterPreset()
        self.assertEqual(len(all_presets), 0)

    def test_delete_filter_preset_returns_error_for_nonexistent(self):
        """
        Test deleteFilterPreset returns error for non-existent ID.
        """

        with self.assertRaises(RequestFailed):
            self._cc_client.deleteFilterPreset(99999)

        with self.assertRaises(RequestFailed):
            self._cc_client.deleteFilterPreset(88888)

        with self.assertRaises(RequestFailed):
            self._cc_client.deleteFilterPreset(77777)

    def test_delete_filter_preset_only_deletes_specified(self):
        """
        Test deleteFilterPreset only deletes the specified preset.
        """

        preset1 = ttypes.FilterPreset(-1,
                                      "Keep1",
                                      ttypes.ReportFilter(severity=[50]))
        preset2 = ttypes.FilterPreset(-1,
                                      "Delete",
                                      ttypes.ReportFilter(severity=[40]))
        preset3 = ttypes.FilterPreset(-1,
                                      "Keep2",
                                      ttypes.ReportFilter(severity=[30]))

        id1 = self._cc_client.storeFilterPreset(preset1)
        id2 = self._cc_client.storeFilterPreset(preset2)
        id3 = self._cc_client.storeFilterPreset(preset3)

        deleted_preset_id = self._cc_client.deleteFilterPreset(id2)
        self.assertNotEqual(deleted_preset_id, -1)
        self.assertEqual(deleted_preset_id, id2)

        remaining = self._cc_client.listFilterPreset()
        self.assertEqual(len(remaining), 2)

        remaining_ids = [p.id for p in remaining]
        self.assertIn(id1, remaining_ids)
        self.assertIn(id3, remaining_ids)
        self.assertNotIn(id2, remaining_ids)

    def test_delete_filter_preset_can_recreate_after_delete(self):
        """
        Test that a preset can be recreated after deletion.
        """

        preset_name = "RecreateTest"

        preset = ttypes.FilterPreset(-1,
                                     preset_name,
                                     ttypes.ReportFilter(severity=[50]))

        preset_id = self._cc_client.storeFilterPreset(preset)

        deleted_preset_id = self._cc_client.deleteFilterPreset(preset_id)
        self.assertNotEqual(deleted_preset_id, -1)

        all_presets = self._cc_client.listFilterPreset()
        self.assertEqual(len(all_presets), 0)

        new_preset = ttypes.FilterPreset(-1,
                                         preset_name,
                                         ttypes.ReportFilter(severity=[40]))

        new_preset_id = self._cc_client.storeFilterPreset(new_preset)

        self.assertNotEqual(new_preset_id, -1)

        all_presets = self._cc_client.listFilterPreset()
        self.assertEqual(len(all_presets), 1)
        self.assertEqual(all_presets[0].name, preset_name)
        self.assertEqual(all_presets[0].reportFilter.severity, [40])


if __name__ == '__main__':
    unittest.main()
