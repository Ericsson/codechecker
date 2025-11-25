#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Component related tests.
"""


import os
import shutil
import sys
import unittest
import uuid

from codechecker_api_shared.ttypes import Permission

from codechecker_api.codeCheckerDBAccess_v6.ttypes import ReportFilter

from libtest import codechecker
from libtest import env
from libtest import project

GEN_OTHER_COMPONENT_NAME = "Other (auto-generated)"


class TestComponent(unittest.TestCase):

    def setup_class(self):
        """Setup the environment for testing components."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('component')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_project = 'cpp'

        test_config = {}

        project_info = project.get_info(test_project)

        test_project_path = os.path.join(TEST_WORKSPACE, "test_proj")
        shutil.copytree(project.path(test_project), test_project_path)

        project_info['project_path'] = test_project_path

        test_project_name = project_info['name'] + '_' + uuid.uuid4().hex

        test_config['test_project'] = project_info

        suppress_file = None

        skip_list_file = None

        test_env = env.test_env(TEST_WORKSPACE)

        codechecker_cfg = {
            'suppress_file': suppress_file,
            'skip_list_file': skip_list_file,
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'checkers': ['-d', 'clang-diagnostic'],
            'analyzers': ['clangsa', 'clang-tidy']
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server(auth_required=True)
        server_access['viewer_product'] = 'component'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # Clean the test project, if needed by the tests.
        ret = project.clean(test_project_path)
        if ret:
            sys.exit(ret)

        ret = codechecker.check_and_store(codechecker_cfg,
                                          test_project_name,
                                          test_project_path)
        if ret:
            sys.exit(1)
        print("Analyzing test project was succcessful.")

        # Save the run names in the configuration.
        codechecker_cfg['run_names'] = [test_project_name]

        test_config['codechecker_cfg'] = codechecker_cfg

        # Export the test configuration to the workspace.
        env.export_test_cfg(TEST_WORKSPACE, test_config)

    def teardown_class(self):
        """Clean up after the test."""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        check_env = env.import_test_cfg(TEST_WORKSPACE)[
            'codechecker_cfg']['check_env']
        codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, _):
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

        # Create a PRODUCT_ADMIN login.
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

        runs = self._cc_client.getRunData(None, None, 0, None)

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
                                    '-*/call_and_message.cpp'])
            },
            {
                'name': 'complex2',
                'value': '\n'.join(['+*/null_dereference.cpp',
                                    '-*/new_delete.cpp'])
            },
            {
                'name': 'exclude_all',
                'value': '-*'
            }
        ]

    def teardown_method(self, _):
        self.__remove_all_source_componens()

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

    def __get_user_defined_source_components(self):
        """ Get user defined source components. """
        components = self._cc_client.getSourceComponents(None)
        self.assertNotEqual(len(components), 0)

        return [c for c in components
                if GEN_OTHER_COMPONENT_NAME not in c.name]

    def __remove_all_source_componens(self):
        print(self.__get_user_defined_source_components())
        for component in self.__get_user_defined_source_components():
            self.__remove_source_component(component.name)

    def __test_other_component(self, components, excluded_from_other,
                               included_in_other=None):
        """
        Test that the results filtered by the given components and the Other
        components covers all the reports and the results filtered by the
        Other component doesn't contain reports which are covered by rest of
        the component.
        """
        all_results = self._cc_client.getRunResults(
            None, 500, 0, None, ReportFilter(), None, False)

        r_filter = ReportFilter(componentNames=[c['name'] for c in components])
        component_results = self._cc_client.getRunResults(None, 500, 0, None,
                                                          r_filter, None,
                                                          False)
        self.assertNotEqual(len(component_results), 0)

        r_filter = ReportFilter(componentNames=[GEN_OTHER_COMPONENT_NAME])
        other_results = self._cc_client.getRunResults(None, 500, 0, None,
                                                      r_filter, None, False)
        self.assertNotEqual(len(other_results), 0)

        self.assertEqual(len(all_results),
                         len(component_results) + len(other_results))

        for f_path in excluded_from_other:
            self.assertEqual(len([r for r in other_results if
                                  r.checkedFile.endswith(f_path)]), 0)

        if included_in_other:
            for f_path in included_in_other:
                self.assertNotEqual(len([r for r in other_results if
                                         r.checkedFile.endswith(f_path)]), 0)

    def test_component_management(self):
        """
        Test management of the components.
        """
        test_component = self.components[0]

        # There are no user defined source components available.
        components = self.__get_user_defined_source_components()
        self.assertEqual(len(components), 0)

        self.__add_new_component(test_component)

        components = self.__get_user_defined_source_components()
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0].name, test_component['name'])
        self.assertEqual(components[0].value, test_component['value'])
        self.assertEqual(components[0].description,
                         test_component['description'])

        self.__remove_source_component(test_component['name'])

        # There are no user defined source components available.
        components = self.__get_user_defined_source_components()
        self.assertEqual(len(components), 0)

    def test_filter_report_by_component(self):
        """
        Test report filter by component.
        """
        test_component = self.components[0]

        components = self.__get_user_defined_source_components()
        self.assertEqual(len(components), 0)

        self.__add_new_component(test_component)

        r_filter = ReportFilter(componentNames=[test_component['name']])
        run_results = self._cc_client.getRunResults(None,
                                                    500,
                                                    0,
                                                    None,
                                                    r_filter,
                                                    None,
                                                    False)
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

        # No reports should be listed which is not in an inclusion or if
        # it is an exclusion filter.

        divide_zero_reports = [r for r in run_results if
                               r.checkedFile.endswith('null_dereference.cpp')]
        self.assertEqual(len(divide_zero_reports), 0)

    def test_filter_report_by_complex_component(self):
        """
        Test report filter by complex component which includes and excludes
        multiple file paths.
        """
        test_component = self.components[2]

        components = self.__get_user_defined_source_components()
        self.assertEqual(len(components), 0)

        self.__add_new_component(test_component)

        r_filter = ReportFilter(componentNames=[test_component['name']])
        run_results = self._cc_client.getRunResults(None,
                                                    500,
                                                    0,
                                                    None,
                                                    r_filter,
                                                    None,
                                                    False)
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

        # No reports should be listed which is not in an inclusion or if
        # it is in an exclusion filter.
        divide_zero_reports = [r for r in run_results if
                               r.checkedFile.endswith('path_begin.cpp')]
        self.assertEqual(len(divide_zero_reports), 0)

    def test_filter_report_by_multiple_components(self):
        """
        Test report filter by multiple components.
        """
        test_component1 = self.components[3]
        test_component2 = self.components[4]

        components = self.__get_user_defined_source_components()
        self.assertEqual(len(components), 0)

        self.__add_new_component(test_component1)
        self.__add_new_component(test_component2)

        components = self.__get_user_defined_source_components()
        self.assertEqual(len(components), 2)

        r_filter = ReportFilter(componentNames=[test_component1['name'],
                                                test_component2['name']])

        run_results = self._cc_client.getRunResults(None,
                                                    500,
                                                    0,
                                                    None,
                                                    r_filter,
                                                    None,
                                                    False)
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

    def test_filter_report_by_excluding_all_results_component(self):
        """
        Test report filter by component which excludes all reports.
        """
        test_component = self.components[5]

        components = self.__get_user_defined_source_components()
        self.assertEqual(len(components), 0)

        self.__add_new_component(test_component)

        r_filter = ReportFilter(componentNames=[test_component['name']])
        run_results = self._cc_client.getRunResults(None,
                                                    500,
                                                    0,
                                                    None,
                                                    r_filter,
                                                    None,
                                                    False)
        self.assertIsNotNone(run_results)

        # No reports for this component.
        self.assertEqual(len(run_results), 0)

    def test_component_name_with_whitespaces(self):
        """
        Creates a new component which contains white spaces and removes it at
        the end of test case.
        """
        test_component = self.components[1]

        self.__add_new_component(test_component)

    def test_no_user_defined_component(self):
        """
        When there is no user defined component in the database, the
        auto-generated Other component will not filter the results.
        """
        components = self.__get_user_defined_source_components()
        self.assertEqual(len(components), 0)

        all_results = self._cc_client.getRunResults(
            None, 500, 0, None, ReportFilter(), None, False)
        self.assertIsNotNone(all_results)

        r_filter = ReportFilter(componentNames=[GEN_OTHER_COMPONENT_NAME])
        other_results = self._cc_client.getRunResults(None, 500, 0, None,
                                                      r_filter, None, False)

        self.assertEqual(len(all_results), len(other_results))

    def test_other_with_single_user_defined_component(self):
        """
        Test that the Other component will not contain reports which are
        covered by a single component.
        """
        component = {
            'name': 'UserDefined',
            'value': '\n'.join(['+*/divide_zero.cpp',
                                '+*/new_delete.cpp'])}

        self.__add_new_component(component)

        excluded_from_other = ['divide_zero.cpp', 'new_delete.cpp']
        self.__test_other_component([component], excluded_from_other)

    def test_other_with_multiple_user_defined_component(self):
        """
        Test that the Other component will not contain reports which are
        covered by multiple components.
        """
        components = [
            {
                'name': 'UserDefined1',
                'value':  '\n'.join([
                    '+*/divide_zero.cpp',
                    '+*/new_delete.cpp'
                ])
            },
            {
                'name': 'UserDefined2',
                'value': '\n'.join([
                    '-*/stack_address_escape.cpp',
                    '-*/new_delete.cpp',
                    '-*/call_and_message.cpp'
                ])
            },
            {
                'name': 'UserDefined3',
                'value': '\n'.join([
                    '+*/null_dereference.cpp',
                    '-*/call_and_message.cpp',
                ])
            }
        ]

        for c in components:
            self.__add_new_component(c)

        excluded_from_other = ['divide_zero.cpp', 'new_delete.cpp',
                               'null_dereference.cpp']

        included_in_other = ['call_and_message.cpp',
                             'stack_address_escape.cpp']

        self.__test_other_component(components, excluded_from_other,
                                    included_in_other)

    def test_component_anywhere_on_path(self):
        """
        Check "anywhere on report path" feature. With this flag one can query
        all reports where the bug path not only ends in the component, but any
        point of the bug path is inside the component.
        """
        components = [
            {
                'name': 'pb1cpp',
                'value': '+*/path_begin1.cpp'
            },
            {
                'name': 'pb2cpp',
                'value': '+*/path_begin2.cpp'
            },
            {
                'name': 'peh',
                'value': '+*/path_end.h'
            }
        ]

        for c in components:
            self.__add_new_component(c)

        r_filter = ReportFilter(componentNames=['peh'])
        component_results = self._cc_client.getRunResults(
            None, 500, 0, None, r_filter, None, False)

        self.assertEqual(len(component_results), 3)
        self.assertTrue(
            all(c.checkedFile.endswith('path_end.h')
                for c in component_results))

        r_filter = ReportFilter(componentNames=['pb1cpp'])
        component_results = self._cc_client.getRunResults(
            None, 500, 0, None, r_filter, None, False)
        self.assertEqual(len(component_results), 0)

        r_filter = ReportFilter(
            componentNames=['pb1cpp'],
            componentMatchesAnyPoint=True)
        component_results = self._cc_client.getRunResults(
            None, 500, 0, None, r_filter, None, False)
        self.assertEqual(len(component_results), 1)
        self.assertTrue(
            component_results[0].checkedFile.endswith('path_end.h'))

    def test_full_report_path_in_component(self):
        """
        Check "full report path in component" feature. With this flag one can
        query all reports where the bug path not only ends in the component,
        but every point of the bug path is inside the component.
        """
        components = [
            {
                'name': 'main',
                'value': '+*/same_origin.cpp'
            },
            {
                'name': 'calculate',
                'value': '+*/calculate.h'
            }
        ]

        for c in components:
            self.__add_new_component(c)

        self.assertEqual(len(components), 2)

        r_filter = ReportFilter(
            componentNames=['calculate'],
            fullReportPathInComponent=False
        )
        component_results = self._cc_client.getRunResults(
            None, 500, 0, None, r_filter, None, False)
        self.assertEqual(len(component_results), 2)
        self.assertEqual(component_results[0].checkerId, 'core.DivideZero')
        self.assertEqual(component_results[1].checkerId,
                         'misc-definitions-in-headers')

        r_filter = ReportFilter(
            componentNames=['calculate'],
            fullReportPathInComponent=True)
        component_results = self._cc_client.getRunResults(
            None, 500, 0, None, r_filter, None, False)
        self.assertEqual(len(component_results), 1)
        self.assertEqual(component_results[0].checkerId,
                         'misc-definitions-in-headers')
