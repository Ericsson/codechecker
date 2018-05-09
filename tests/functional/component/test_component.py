#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

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

        self._component_name = 'dummy_component'
        self._component_value = '\n'.join(['+*/divide_zero.cpp',
                                           '-*/new_delete.cpp'])
        self._component_description = "Test component"

    def test_component_management(self):
        """
        Test management of the components.
        """
        # There are no source components available.
        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 0)

        # Create a new source component.
        ret = self._cc_client.addSourceComponent(self._component_name,
                                                 self._component_value,
                                                 self._component_description)
        self.assertTrue(ret)

        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0].name, self._component_name)
        self.assertEqual(components[0].value, self._component_value)
        self.assertEqual(components[0].description,
                         self._component_description)

        ret = self._cc_client.removeSourceComponent(self._component_name)
        self.assertTrue(ret)

        # There are no source components available.
        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 0)

    def test_filter_report_by_component(self):
        """
        Test report filter by component.
        """
        components = self._cc_client.getSourceComponents(None)
        self.assertEqual(len(components), 0)

        # Create a new source component.
        ret = self._cc_client.addSourceComponent(self._component_name,
                                                 self._component_value,
                                                 self._component_description)
        self.assertTrue(ret)

        r_filter = ReportFilter(componentNames=[self._component_name])
        run_results = self._cc_client.getRunResults(None,
                                                    500,
                                                    0,
                                                    None,
                                                    r_filter,
                                                    None)
        self.assertIsNotNone(run_results)
        divide_zero_reports = [r for r in run_results if
                               r.checkedFile.endswith('divide_zero.cpp')]
        self.assertNotEqual(len(divide_zero_reports), 0)

        divide_zero_reports = [r for r in run_results if
                               r.checkedFile.endswith('new_delete.cpp')]
        self.assertEqual(len(divide_zero_reports), 0)

    def test_component_name_with_whitespaces(self):
        component_name = 'component name with whitespaces'
        ret = self._cc_client.addSourceComponent(component_name,
                                                 "",
                                                 None)
        self.assertTrue(ret)

        ret = self._cc_client.removeSourceComponent(component_name)
        self.assertTrue(ret)
