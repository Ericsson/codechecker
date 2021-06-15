#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test product management related features.
"""


from copy import deepcopy
import os
import unittest

from codechecker_api_shared.ttypes import RequestFailed
from codechecker_api_shared.ttypes import DBStatus
from codechecker_api.ProductManagement_v6.ttypes import ProductConfiguration
from codechecker_api.ProductManagement_v6.ttypes import DatabaseConnection

from codechecker_web.shared import convert

from libtest import env


class TestProducts(unittest.TestCase):

    def setUp(self):
        """
        """

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the test configuration from the prepared int the test workspace.
        self.test_cfg = env.import_test_cfg(self.test_workspace)

        self.product_name = self.test_cfg['codechecker_cfg']['viewer_product']

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Setup an authentication client for creating sessions.
        self._auth_client = env.setup_auth_client(self.test_workspace,
                                                  session_token='_PROHIBIT')

        # Create a SUPERUSER login.
        root_token = self._auth_client.performLogin("Username:Password",
                                                    "root:root")

        # Setup a product client to test product API calls.
        self._pr_client = env.setup_product_client(self.test_workspace)
        self.assertIsNotNone(self._pr_client)

        # Setup a product client to test product API calls which requires root.
        self._root_client = env.setup_product_client(self.test_workspace,
                                                     session_token=root_token)
        self.assertIsNotNone(self._pr_client)

        # Get the run names which belong to this test.
        run_names = env.get_run_names(self.test_workspace)

        runs = self._cc_client.getRunData(None, None, 0, None)
        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         "There should be only one run for this test.")
        self._runid = test_runs[0].runId

    def test_add_invalid_product(self):
        """
        Test the server prohibiting the addition of bogus product configs.
        """
        error = convert.to_b64("bogus")
        product_cfg = ProductConfiguration(
            displayedName_b64=error,
            description_b64=error
        )

        # Test setting up product with valid endpoint but no database
        # connection.
        with self.assertRaises(RequestFailed):
            cfg = deepcopy(product_cfg)
            cfg.endpoint = "valid"
            self._root_client.addProduct(cfg)

        # Test some invalid strings based on pattern.
        dbc = DatabaseConnection(
            engine='sqlite',
            host='',
            port=0,
            username_b64='',
            password_b64='',
            database="valid.sqlite"
        )
        product_cfg.connection = dbc

        with self.assertRaises(RequestFailed):
            product_cfg.endpoint = "$$$$$$$"
            self._root_client.addProduct(product_cfg)

        # Test some forbidden URI parts.
        with self.assertRaises(RequestFailed):
            product_cfg.endpoint = "index.html"
            self._root_client.addProduct(product_cfg)

        with self.assertRaises(RequestFailed):
            product_cfg.endpoint = "CodeCheckerService"
            self._root_client.addProduct(product_cfg)

    def test_get_product_data(self):
        """
        Test getting product configuration from server.
        """

        # First, test calling the API through a product endpoint and not the
        # global endpoint. Also retrieve product ID this way.
        pr_client = env.setup_product_client(
            self.test_workspace, product=self.product_name)
        self.assertIsNotNone(pr_client, "Couldn't set up client")

        # This returns a USERSPACE product data.
        pr_data = pr_client.getCurrentProduct()

        self.assertIsNotNone(pr_data,
                             "Couldn't retrieve product data properly")

        self.assertEqual(pr_data.endpoint, self.product_name,
                         "The product's endpoint is improper.")
        self.assertTrue(pr_data.id > 0, "Product didn't have valid ID")

        # The connected attribute of a product will be always True if
        # database status is OK.
        connected = pr_data.databaseStatus == DBStatus.OK
        self.assertEqual(pr_data.connected, connected)

        # Now get the SERVERSPACE (configuration) for the product.
        # TODO: These things usually should only work for superusers!
        pr_conf = self._pr_client.getProductConfiguration(pr_data.id)

        self.assertIsNotNone(pr_conf, "Product configuration must come.")
        self.assertEqual(pr_conf.endpoint, self.product_name,
                         "Product endpoint reproted by server must be the "
                         "used endpoint... something doesn't make sense here!")

        self.assertIsNotNone(pr_conf.connection, "Product configuration must "
                             "send a database connection.")

        self.assertIsNone(pr_conf.connection.password_b64,
                          "!SECURITY LEAK! Server should NEVER send the "
                          "product's database password out!")

        self.assertIn(self.product_name, pr_conf.connection.database,
                      "The product's database (name|file) should contain "
                      "the product's endpoint -- in the test context.")

        name = convert.from_b64(pr_conf.displayedName_b64) \
            if pr_conf.displayedName_b64 else ''
        self.assertEqual(name,
                         # libtest/codechecker.py uses the workspace's name.
                         os.path.basename(self.test_workspace),
                         "The displayed name must == the default value, as "
                         "we didn't specify a custom displayed name.")

    def test_editing(self):
        """
        Test editing the product details (without reconnecting it).
        """

        pr_client = env.setup_product_client(
            self.test_workspace, product=self.product_name)
        product_id = pr_client.getCurrentProduct().id
        config = self._pr_client.getProductConfiguration(product_id)

        old_name = config.displayedName_b64

        new_name = convert.to_b64("edited product name")
        config.displayedName_b64 = new_name
        with self.assertRaises(RequestFailed):
            self._pr_client.editProduct(product_id, config)
            print("Product was edited through non-superuser!")

        self.assertTrue(self._root_client.editProduct(product_id, config),
                        "Product edit didn't conclude.")

        config = self._pr_client.getProductConfiguration(product_id)
        self.assertEqual(config.endpoint, self.product_name,
                         "The product edit changed the endpoint, when it "
                         "shouldn't have!")
        self.assertEqual(config.displayedName_b64, new_name,
                         "The product edit didn't change the name.")

        # Restore the configuration of the product.
        config.displayedName_b64 = old_name
        self.assertTrue(self._root_client.editProduct(product_id, config),
                        "Product config restore didn't conclude.")

        config = self._pr_client.getProductConfiguration(product_id)
        self.assertEqual(config.displayedName_b64, old_name,
                         "The product edit didn't change the name back.")

    @unittest.skip("Enable this when local product caches is removed!")
    def test_editing_reconnect(self):
        """
        Test if the product can successfully be set to connect to another db.

        This requires a SUPERUSER.
        """

        pr_client = env.setup_product_client(
            self.test_workspace, product=self.product_name)
        product_id = pr_client.getCurrentProduct().id
        config = self._pr_client.getProductConfiguration(product_id)

        old_db_name = config.connection.database

        # Create a new database.
        tenv = self.test_cfg['codechecker_cfg']['check_env']

        if config.connection.engine == 'sqlite':
            new_db_name = os.path.join(self.test_workspace, 'new.sqlite')
        elif config.connection.engine == 'postgresql':
            new_db_name = 'editeddb'
            env.add_database(new_db_name, tenv)
        else:
            raise ValueError("I was not prepared to handle database mode " +
                             config.connection.engine)

        config.connection.database = new_db_name
        self.assertTrue(self._root_client.editProduct(product_id, config),
                        "Product edit didn't conclude.")

        # Check if the configuration now uses the new values.
        config = self._pr_client.getProductConfiguration(product_id)

        self.assertEqual(config.connection.database, new_db_name,
                         "Server didn't save new database name.")
        self.assertEqual(config.endpoint, self.product_name,
                         "The endpoint was changed -- perhaps the "
                         "temporary connection leaked into the database?")

        # There is no schema initialization if the product database
        # was changed. The inital schema needs to be created manually
        # for the new database.
        runs = self._cc_client.getRunData(None, None, 0, None)
        self.assertIsNone(runs)

        # Connect back to the old database.
        config.connection.database = old_db_name
        self.assertTrue(self._root_client.editProduct(product_id, config),
                        "Product configuration restore didn't conclude.")

        config = self._pr_client.getProductConfiguration(product_id)
        self.assertEqual(config.connection.database, old_db_name,
                         "Server didn't save back to old database name.")

        # The old database should have its data available again.
        runs = self._cc_client.getRunData(None, None, 0, None)
        self.assertEqual(
            len(runs), 1,
            "We connected to old database but the run was missing.")

        # Drop the temporary database. SQLite file will be removed with
        # the test workspace.
        if config.connection.engine == 'postgresql':
            env.del_database(new_db_name, tenv)

    @unittest.skip("Enable this when local product caches is removed!")
    def test_editing_endpoint(self):
        """
        Test if the product can successfully change its endpoint and keep
        the data.
        """

        pr_client = env.setup_product_client(
            self.test_workspace, product=self.product_name)
        product_id = pr_client.getCurrentProduct().id
        config = self._pr_client.getProductConfiguration(product_id)

        old_endpoint = config.endpoint
        new_endpoint = "edited_endpoint"

        # Save a new endpoint.
        config.endpoint = new_endpoint
        self.assertTrue(self._root_client.editProduct(product_id, config),
                        "Product edit didn't conclude.")

        # Check if the configuration now uses the new values.
        config = self._pr_client.getProductConfiguration(product_id)
        self.assertEqual(config.endpoint, new_endpoint,
                         "Server didn't save new endpoint.")

        # The old product is gone. Thus, connection should NOT happen.
        res = self._cc_client.getRunData(None, None, 0, None)
        self.assertIsNone(res)

        # The new product should connect and have the data.
        codechecker_cfg = self.test_cfg['codechecker_cfg']
        token = self._auth_client.performLogin("Username:Password", "cc:test")
        new_client = env.get_viewer_client(
            host=codechecker_cfg['viewer_host'],
            port=codechecker_cfg['viewer_port'],
            product=new_endpoint,  # Use the new product URL.
            endpoint='/CodeCheckerService',
            session_token=token)
        self.assertEqual(len(new_client.getRunData(None, None, 0, None)), 1,
                         "The new product did not serve the stored data.")

        # Set back to the old endpoint.
        config.endpoint = old_endpoint
        self.assertTrue(self._root_client.editProduct(product_id, config),
                        "Product configuration restore didn't conclude.")

        config = self._pr_client.getProductConfiguration(product_id)
        self.assertEqual(config.endpoint, old_endpoint,
                         "Server didn't save back to old endpoint.")

        # The old product should have its data available again.
        runs = self._cc_client.getRunData(None, None, 0, None)
        self.assertEqual(
            len(runs), 1,
            "We connected to old database but the run was missing.")
