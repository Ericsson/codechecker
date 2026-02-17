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

from libtest import codechecker
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
            id=None,
            name="TestPreset",
            reportFilter=report_filter
        )

        preset_id = self._cc_client.storeFilterPreset(preset)

        self.assertNotEqual(preset_id, -1, "Should return valid ID")
        self.assertIsInstance(preset_id, int)
        self.assertGreater(preset_id, 0)

    def test_store_filter_preset_updates_existing(self):
        """
        Test storeFilterPreset updates an existing preset with same name.
        """
        preset_name = "UpdateTest"

        report_filter = ttypes.ReportFilter(severity=[50])
        preset = ttypes.FilterPreset(None, preset_name, report_filter)

        preset_id = self._cc_client.storeFilterPreset(preset)
        self.assertNotEqual(preset_id, -1)

        updated_filter = ttypes.ReportFilter(severity=[50, 40, 30])
        updated_preset = ttypes.FilterPreset(None,
                                             preset_name,
                                             updated_filter)

        new_id = self._cc_client.storeFilterPreset(updated_preset)
        self.assertNotEqual(new_id, -1)

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

        preset = ttypes.FilterPreset(None, "ComplexPreset", report_filter)
        preset_id = self._cc_client.storeFilterPreset(preset)

        self.assertNotEqual(preset_id, -1)
        self.assertGreater(preset_id, 0)

    def test_store_filter_preset_with_empty_filter(self):
        """
        Test storeFilterPreset with empty ReportFilter.
        """
        report_filter = ttypes.ReportFilter()
        preset = ttypes.FilterPreset(None, "EmptyFilter", report_filter)

        preset_id = self._cc_client.storeFilterPreset(preset)

        self.assertNotEqual(preset_id, -1)

    def test_store_filter_preset_returns_minus_one_on_error(self):
        """
        Test storeFilterPreset returns -1 on error.
        """
        try:
            preset = ttypes.FilterPreset(None,
                                         None,
                                         ttypes.ReportFilter())

            preset_id = self._cc_client.storeFilterPreset(preset)

            self.assertEqual(preset_id, -1)
        except Exception:
            pass

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
        preset = ttypes.FilterPreset(None,
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

    def test_get_filter_preset_returns_none_for_nonexistent(self):
        """
        Test getFilterPreset returns None for non-existent ID.
        """

        returned_preset = self._cc_client.getFilterPreset(99999)

        self.assertEqual(returned_preset, -1)

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
        preset = ttypes.FilterPreset(None,
                                     "CompleteTest",
                                     report_filter)

        preset_id = self._cc_client.storeFilterPreset(preset)

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

        preset = ttypes.FilterPreset(None,
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

        preset1 = ttypes.FilterPreset(None,
                                      "Preset1",
                                      ttypes.ReportFilter(severity=[50]))
        preset2 = ttypes.FilterPreset(None,
                                      "Preset2",
                                      ttypes.ReportFilter(severity=[40]))
        preset3 = ttypes.FilterPreset(None,
                                      "Preset3",
                                      ttypes.ReportFilter(severity=[30]))

        id1 = self._cc_client.storeFilterPreset(preset1)
        id2 = self._cc_client.storeFilterPreset(preset2)
        id3 = self._cc_client.storeFilterPreset(preset3)

        presets = self._cc_client.listFilterPreset()

        self.assertEqual(len(presets), 3)

        preset_ids = [p.id for p in presets]
        self.assertIn(id1, preset_ids)
        self.assertIn(id2, preset_ids)
        self.assertIn(id3, preset_ids)

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

        preset1 = ttypes.FilterPreset(None,
                                      "WithFilter1",
                                      report_filter_1)

        preset2 = ttypes.FilterPreset(None,
                                      "WithFilter2",
                                      report_filter_2)

        id1 = self._cc_client.storeFilterPreset(preset1)
        id2 = self._cc_client.storeFilterPreset(preset2)

        self.assertNotEqual(id1, -1)
        self.assertNotEqual(id2, -1)

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

        preset = ttypes.FilterPreset(None,
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

        deleted_preset_id = self._cc_client.deleteFilterPreset(99999)

        self.assertEqual(deleted_preset_id, -1)

    def test_delete_filter_preset_only_deletes_specified(self):
        """
        Test deleteFilterPreset only deletes the specified preset.
        """

        preset1 = ttypes.FilterPreset(None,
                                      "Keep1",
                                      ttypes.ReportFilter(severity=[50]))
        preset2 = ttypes.FilterPreset(None,
                                      "Delete",
                                      ttypes.ReportFilter(severity=[40]))
        preset3 = ttypes.FilterPreset(None,
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

        preset = ttypes.FilterPreset(None,
                                     preset_name,
                                     ttypes.ReportFilter(severity=[50]))

        preset_id = self._cc_client.storeFilterPreset(preset)

        deleted_preset_id = self._cc_client.deleteFilterPreset(preset_id)
        self.assertNotEqual(deleted_preset_id, -1)

        all_presets = self._cc_client.listFilterPreset()
        self.assertEqual(len(all_presets), 0)

        new_preset = ttypes.FilterPreset(None,
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
