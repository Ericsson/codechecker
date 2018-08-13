#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Component related tests.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import unittest

from shared.ttypes import Permission

from codeCheckerDBAccess_v6.ttypes import ReportFilter

from libtest import env


class TestComponent(unittest.TestCase):

    def setUp(self):
        self._test_workspace = os.environ.get('TEST_WORKSPACE')

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

        self._clang_to_test = env.clang_to_test()

        self._testproject_data = env.setup_test_proj_cfg(self._test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Get the test configuration from the prepared int the test workspace.
        self.test_cfg = env.import_test_cfg(self._test_workspace)

        self._product_name = self.test_cfg['codechecker_cfg']['viewer_product']
        pr_client = env.setup_product_client(
            self._test_workspace, product=self._product_name)
        product_id = pr_client.getCurrentProduct().id

        # Setup an authentication client for creating sessions.
        self._auth_client = env.setup_auth_client(self._test_workspace,
                                                  session_token='_PROHIBIT')

        # Create an PRODUCT_ADMIN login.
        admin_token = self._auth_client.performLogin("Username:Password",
                                                     "admin:admin123")

        extra_params = '{"productID":' + str(product_id) + '}'
        ret = self._auth_client.addPermission(Permission.PRODUCT_ADMIN,
                                              "admin",
                                              False,
                                              extra_params)
        self.assertTrue(ret)

        self._cc_client = env.setup_viewer_client(self._test_workspace,
                                                  session_token=admin_token)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test
        run_names = env.get_run_names(self._test_workspace)

        runs = self._cc_client.getRunData(None)

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         'There should be only one run for this test.')
        self._runid = test_runs[0].runId
        self._run_name = test_runs[0].name

        self.components = [
            {
                'name': 'test_component1',
                'value': '\n'.join(['+*/divide_zero.cpp',
                                    '-*/new_delete.cpp']),
                'description': 'Description of my first component'
            },
            {
                'name': 'component name with whitespaces',
                'value': '\n'.join(['+*/divide_zero.cpp',
                                    '-*/new_delete.cpp']),
                'description': 'Description of my second component'
            },
            {
                'name': 'test_component2',
                'value': '\n'.join(['+*/divide_zero.cpp',
                                    '+*/null_dereference.cpp',
                                    '-*/call_and_message.cpp',
                                    '-*/new_delete.*']),
                'description': 'Description of my second component'
            },
            {
                'name': 'complex1',
                'value': '\n'.join(['+*/divide_zero.cpp',
                                    '-*/call_and_message.cpp',
                                    '-*'])
            },
            {
                'name': 'complex2',
                'value': '\n'.join(['+*/null_dereference.cpp',
                                    '-*/new_delete.cpp',
                                    '-*'])
            },
            {
                'name': 'exclude_all',
                'value': '-*'
            }
        ]

    def __add_new_component(self, component):
        """
        Creates a new source component.
        """
        description = component['description'] \
            if 'description' in component else None
        ret = self._cc_client.addSourceComponent(component['name'],
                                                 component['value'],
                                                 description)

        self.assertTrue(ret)

    def __remove_source_component(self, name):
        """
        Removes an existing source component.
        """
        ret = self._cc_client.removeSourceComponent(name)
        self.assertTrue(ret)

    def test_component_management(self):
        """
        Test management of the components.
        """
        test_component = self.components[0]

        # There are no source components available.
        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 0)

        self.__add_new_component(test_component)

        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0].name, test_component['name'])
        self.assertEqual(components[0].value, test_component['value'])
        self.assertEqual(components[0].description,
                         test_component['description'])

        self.__remove_source_component(test_component['name'])

        # There are no source components available.
        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 0)

    def test_filter_report_by_component(self):
        """
        Test report filter by component.
        """
        test_component = self.components[0]

        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 0)

        self.__add_new_component(test_component)

        r_filter = ReportFilter(componentNames=[test_component['name']])
        run_results = self._cc_client.getRunResults(None,
                                                    500,
                                                    0,
                                                    None,
                                                    r_filter,
                                                    None)
        self.assertIsNotNone(run_results)

        # Check that reports which can be found in file what the source
        # component including are in the filtered results.
        divide_zero_reports = [r for r in run_results if
                               r.checkedFile.endswith('divide_zero.cpp')]
        self.assertNotEqual(len(divide_zero_reports), 0)

        # Check that reports which can be found in file what the source
        # component excluding are in the filtered results.
        new_delete_reports = [r for r in run_results if
                              r.checkedFile.endswith('new_delete.cpp')]
        self.assertEqual(len(new_delete_reports), 0)

        # Check that reports which can be found in file what the source
        # component does not includes or excludes are in the filtered results.
        divide_zero_reports = [r for r in run_results if
                               r.checkedFile.endswith('null_dereference.cpp')]
        self.assertNotEqual(len(divide_zero_reports), 0)

        self.__remove_source_component(test_component['name'])

    def test_filter_report_by_complex_component(self):
        """
        Test report filter by complex component which includes and excludes
        multiple file paths.
        """
        test_component = self.components[2]

        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 0)

        self.__add_new_component(test_component)

        r_filter = ReportFilter(componentNames=[test_component['name']])
        run_results = self._cc_client.getRunResults(None,
                                                    500,
                                                    0,
                                                    None,
                                                    r_filter,
                                                    None)
        self.assertIsNotNone(run_results)

        # Check that reports which can be found in file what the source
        # component including are in the filtered results.
        divide_zero_reports = [r for r in run_results if
                               r.checkedFile.endswith('divide_zero.cpp')]
        self.assertNotEqual(len(divide_zero_reports), 0)

        null_deref_reports = [r for r in run_results if
                              r.checkedFile.endswith('null_dereference.cpp')]
        self.assertNotEqual(len(null_deref_reports), 0)

        # Check that reports which can be found in file what the source
        # component excluding are in the filtered results.
        new_delete_reports = [r for r in run_results if
                              r.checkedFile.endswith('new_delete.cpp')]
        self.assertEqual(len(new_delete_reports), 0)

        call_and_msg_reports = [r for r in run_results if
                                r.checkedFile.endswith('call_and_message.cpp')]
        self.assertEqual(len(call_and_msg_reports), 0)

        # Check that reports which can be found in file what the source
        # component does not includes or excludes are in the filtered results.
        divide_zero_reports = [r for r in run_results if
                               r.checkedFile.endswith('path_begin.cpp')]
        self.assertNotEqual(len(divide_zero_reports), 0)

        self.__remove_source_component(test_component['name'])

    def test_filter_report_by_multiple_components(self):
        """
        Test report filter by multiple components.
        """
        test_component1 = self.components[3]
        test_component2 = self.components[4]

        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 0)

        self.__add_new_component(test_component1)
        self.__add_new_component(test_component2)

        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 2)

        r_filter = ReportFilter(componentNames=[test_component1['name'],
                                                test_component2['name']])
        run_results = self._cc_client.getRunResults(None,
                                                    500,
                                                    0,
                                                    None,
                                                    r_filter,
                                                    None)
        self.assertIsNotNone(run_results)

        # Check that reports which can be found in file what the source
        # component including are in the filtered results.
        divide_zero_reports = [r for r in run_results if
                               r.checkedFile.endswith('divide_zero.cpp')]
        self.assertNotEqual(len(divide_zero_reports), 0)

        null_deref_reports = [r for r in run_results if
                              r.checkedFile.endswith('null_dereference.cpp')]
        self.assertNotEqual(len(null_deref_reports), 0)

        # Check that reports which can be found in file what the source
        # component excluding are in the filtered results.
        new_delete_reports = [r for r in run_results if
                              r.checkedFile.endswith('new_delete.cpp')]
        self.assertEqual(len(new_delete_reports), 0)

        call_and_msg_reports = [r for r in run_results if
                                r.checkedFile.endswith('call_and_message.cpp')]
        self.assertEqual(len(call_and_msg_reports), 0)

        self.__remove_source_component(test_component1['name'])
        self.__remove_source_component(test_component2['name'])

    def test_filter_report_by_excluding_all_results_component(self):
        """
        Test report filter by component which excludes all reports.
        """
        test_component = self.components[5]

        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 0)

        self.__add_new_component(test_component)

        r_filter = ReportFilter(componentNames=[test_component['name']])
        run_results = self._cc_client.getRunResults(None,
                                                    500,
                                                    0,
                                                    None,
                                                    r_filter,
                                                    None)
        self.assertIsNotNone(run_results)

        # No reports for this component.
        self.assertEqual(len(run_results), 0)

        self.__remove_source_component(test_component['name'])

    def test_component_name_with_whitespaces(self):
        """
        Creates a new component which contains white spaces and removes it at
        the end of test case.
        """
        test_component = self.components[1]

        self.__add_new_component(test_component)
        self.__remove_source_component(test_component['name'])
