#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test accessing products that were added in a "Shared configuration database"
environment.
"""


from copy import deepcopy
import multiprocessing
import os
import shutil
import unittest

from codechecker_api_shared.ttypes import Permission

from codechecker_api.ProductManagement_v6.ttypes import ProductConfiguration
from codechecker_api.ProductManagement_v6.ttypes import DatabaseConnection

from codechecker_web.shared import convert

from libtest import codechecker
from libtest import env

# Stopping events for CodeChecker server.
EVENT = multiprocessing.Event()


class TestProductConfigShare(unittest.TestCase):

    def setUp(self):
        """
        Set up the environment and the test module's configuration from the
        package.
        """

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace_main = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' +
              self.test_workspace_main)

        # Set up a configuration for the main server.
        # Get the test configuration from the prepared int the test workspace.
        self.test_cfg = env.import_test_cfg(self.test_workspace_main)

        self.product_name = self.test_cfg['codechecker_cfg']['viewer_product']

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace_main)
        self.assertIsNotNone(self._cc_client)

        # Setup an authentication client for creating sessions.
        self._auth_client = env.setup_auth_client(self.test_workspace_main,
                                                  session_token='_PROHIBIT')

        # Create a SUPERUSER login.
        root_token = self._auth_client.performLogin("Username:Password",
                                                    "root:root")

        # Add SUPERUSER permission to the root user and test that the white
        # spaces are being removed from the user name.
        ret = self._auth_client.addPermission(Permission.SUPERUSER,
                                              "  root  ",
                                              False,
                                              "")
        self.assertTrue(ret)

        # Setup a product client to test product API calls.
        self._pr_client = env.setup_product_client(self.test_workspace_main)
        self.assertIsNotNone(self._pr_client)

        # Setup a product client to test product API calls which requires root.
        self._root_client = env.setup_product_client(self.test_workspace_main,
                                                     session_token=root_token)
        self.assertIsNotNone(self._root_client)

        # Get the run names which belong to this test.
        run_names = env.get_run_names(self.test_workspace_main)

        runs = self._cc_client.getRunData(None, None, 0, None)
        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         "There should be only one run for this test.")
        self._runid = test_runs[0].runId

        # Start a second server with the same configuration database as the
        # main one.
        self.test_workspace_secondary = env.get_workspace('producttest_second')
        self.codechecker_cfg_2 = {
            'check_env': self.test_cfg['codechecker_cfg']['check_env'],
            'workspace': self.test_workspace_secondary,
            'checkers': [],
            'viewer_host': 'localhost',
            'viewer_port': env.get_free_port(),
            'viewer_product': 'producttest_second'
        }
        self.codechecker_cfg_2['check_env']['HOME'] = \
            self.test_workspace_secondary
        env.export_test_cfg(self.test_workspace_secondary,
                            {'codechecker_cfg': self.codechecker_cfg_2})

        server_config = dict(self.codechecker_cfg_2)
        server_config['workspace'] = os.path.join(env.get_workspace(None),
                                                  'global_auth_server')

        codechecker.start_server(server_config, EVENT, None,
                                 env.get_postgresql_cfg())

        # Set up API clients for the secondary server.
        self._auth_client_2 = env.setup_auth_client(
            self.test_workspace_secondary, session_token='_PROHIBIT')
        root_token_2 = self._auth_client_2.performLogin("Username:Password",
                                                        "root:root")
        self._pr_client_2 = env.setup_product_client(
            self.test_workspace_secondary, session_token=root_token_2)
        self.assertIsNotNone(self._pr_client_2)

    def test_read_product_from_another_server(self):
        """
        Test if adding and removing a product is visible from the other server.
        """

        # Check if the main server's product is visible on the second server.
        self.assertEqual(
            self._pr_client_2.getProducts('producttest', None)[0].endpoint,
            'producttest',
            "Main server's product was not loaded by the secondary server.")

        def create_test_product(product_name, product_endpoint):
            # Create a new product on the secondary server.
            name = convert.to_b64(product_name)
            return ProductConfiguration(
                endpoint=product_endpoint,
                displayedName_b64=name,
                description_b64=name,
                connection=DatabaseConnection(
                    engine='sqlite',
                    host='',
                    port=0,
                    username_b64='',
                    password_b64='',
                    database=os.path.join(self.test_workspace_secondary,
                                          'data.sqlite')))

        product_cfg = create_test_product('producttest_second',
                                          'producttest_second')

        self.assertTrue(self._pr_client_2.addProduct(product_cfg),
                        "Cannot create product on secondary server.")

        product_cfg = create_test_product('producttest_second 2',
                                          'producttest_second_2')
        self.assertTrue(self._pr_client_2.addProduct(product_cfg),
                        "Cannot create product on secondary server.")

        # Product name full string match.
        products = self._pr_client_2.getProducts('producttest_second', None)
        self.assertEqual(len(products), 1)

        # Product endpoint full string match.
        products = self._pr_client_2.getProducts(None, 'producttest_second')
        self.assertEqual(len(products), 1)

        # Product name substring match.
        products = self._pr_client_2.getProducts('producttest_second*', None)
        self.assertEqual(len(products), 2)

        products = self._pr_client_2.getProducts(None, 'producttest_second*')
        self.assertEqual(len(products), 2)

        # Use the same CodeChecker config that was used on the main server,
        # but store into the secondary one.
        store_cfg = deepcopy(self.test_cfg['codechecker_cfg'])
        store_cfg.update({
            'viewer_port': self.codechecker_cfg_2['viewer_port'],
            'viewer_product': self.codechecker_cfg_2['viewer_product']})
        codechecker.login(store_cfg,
                          self.test_workspace_secondary,
                          'root', 'root')
        store_cfg['reportdir'] = os.path.join(self.test_workspace_main,
                                              'reports')
        store_res = codechecker.store(store_cfg, 'test_proj-secondary')
        self.assertEqual(store_res, 0, "Storing the test project failed.")

        cc_client_2 = env.setup_viewer_client(self.test_workspace_secondary)
        self.assertEqual(len(cc_client_2.getRunData(None, None, 0, None)), 1,
                         "There should be a run present in the new server.")

        self.assertEqual(len(self._cc_client.getRunData(None, None, 0, None)),
                         1,
                         "There should be a run present in the database when "
                         "connected through the main server.")

        # Remove the product through the main server.
        p_id = self._root_client.getProducts('producttest_second', None)[0].id
        p_id2 = self._pr_client_2.getProducts('producttest_second', None)[0].id
        self.assertIsNotNone(p_id)
        self.assertEqual(p_id, p_id2,
                         "The products have different ID across the two "
                         "servers. WHAT? Database isn't shared?!")

        self.assertTrue(self._root_client.removeProduct(p_id),
                        "Main server reported error while removing product.")

        self.assertEqual(len(self._pr_client_2.getProducts('_second', None)),
                         0,
                         "Secondary server still sees the removed product.")

        # Try to store into the product just removed through the secondary
        # server, which still sees the product internally.
        store_res = codechecker.store(store_cfg, 'test_proj-secondary')
        self.assertNotEqual(store_res, 0, "Storing into the server with "
                            "the product missing should've resulted in "
                            "an error.")

    def tearDown(self):
        """
        Clean the environment after running this test module
        """

        # Let the secondary CodeChecker servers die.
        EVENT.set()

        print("Removing: " + self.test_workspace_secondary)
        shutil.rmtree(self.test_workspace_secondary, ignore_errors=True)
