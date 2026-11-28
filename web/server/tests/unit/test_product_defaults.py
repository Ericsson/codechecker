# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Unit tests for the default database connection settings of new products
("product_defaults.connection" section of the server configuration file).
"""


import json
import os
import stat
import tempfile
import unittest

from codechecker_server.session_manager import SessionManager, \
    get_product_default_connection


def _write_json(path, data):
    """Write ``data`` as JSON to ``path`` and restrict permissions to 0600."""
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def _config(connection):
    """Create a minimal server configuration with the given connection."""
    return {
        "authentication": {"enabled": False},
        "product_defaults": {"connection": connection}
    }


class ProductDefaultConnectionTest(unittest.TestCase):
    """
    Testing the parsing of the "product_defaults.connection" section.
    """

    def test_missing_section(self):
        """No defaults are returned if the section is missing."""
        self.assertEqual(get_product_default_connection({}), {})
        self.assertEqual(
            get_product_default_connection({"product_defaults": None}), {})
        self.assertEqual(
            get_product_default_connection({"product_defaults": {}}), {})

    def test_null_values(self):
        """Keys with null values are skipped."""
        connection = {
            "engine": None,
            "host": None,
            "port": None,
            "username": None
        }
        self.assertEqual(
            get_product_default_connection(_config(connection)), {})

    def test_full_postgresql_connection(self):
        """Every supported key is returned if it is valid."""
        connection = {
            "engine": "postgresql",
            "host": "db.test.org",
            "port": 5432,
            "username": "codechecker"
        }
        self.assertEqual(
            get_product_default_connection(_config(connection)), connection)

    def test_partial_connection(self):
        """Only the configured keys are returned."""
        connection = {"engine": "sqlite"}
        self.assertEqual(
            get_product_default_connection(_config(connection)),
            {"engine": "sqlite"})

    def test_invalid_values_are_ignored(self):
        """Invalid values are left out, valid ones are kept."""
        connection = {
            "engine": "mysql",
            "host": "",
            "port": 70000,
            "username": 42
        }
        self.assertEqual(
            get_product_default_connection(_config(connection)), {})

        for port in ["5432", True, 0, -1]:
            self.assertEqual(
                get_product_default_connection(_config({"port": port})), {},
                f"Port value {port!r} should be ignored.")

    def test_password_is_never_returned(self):
        """A password in the configuration must never be returned."""
        connection = {
            "engine": "postgresql",
            "username": "codechecker",
            "password": "testpassword"
        }
        defaults = get_product_default_connection(_config(connection))
        self.assertNotIn("password", defaults)
        self.assertEqual(defaults, {"engine": "postgresql",
                                    "username": "codechecker"})

    def test_unknown_keys_are_ignored(self):
        """Keys which are not supported are not returned."""
        connection = {"engine": "postgresql", "database": "products"}
        self.assertEqual(
            get_product_default_connection(_config(connection)),
            {"engine": "postgresql"})

    def test_section_with_wrong_type(self):
        """A section which is not an object is ignored."""
        self.assertEqual(
            get_product_default_connection({"product_defaults": []}), {})
        self.assertEqual(
            get_product_default_connection(
                {"product_defaults": {"connection": "postgresql"}}), {})


class SessionManagerProductDefaultsTest(unittest.TestCase):
    """
    Testing the product defaults through the SessionManager, which reads the
    server configuration file.
    """

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)

        self.config_file = os.path.join(self._tmp_dir.name,
                                        'server_config.json')
        self.secrets_file = os.path.join(self._tmp_dir.name,
                                         'server_secrets.json')

    def test_defaults_from_config_file(self):
        """The defaults are read from the configuration file."""
        connection = {"engine": "postgresql", "host": "db.test.org",
                      "port": 5432, "username": "codechecker"}
        _write_json(self.config_file, _config(connection))

        manager = SessionManager(None, self.config_file, self.secrets_file)

        self.assertEqual(manager.get_product_default_connection(), connection)

    def test_defaults_resolve_env_variables(self):
        """Values can come from environment variables, like other options."""
        _write_json(self.config_file,
                    _config({"host": "$ENV:CC_TEST_PRODUCT_DB_HOST$"}))

        os.environ["CC_TEST_PRODUCT_DB_HOST"] = "env-db.test.org"
        self.addCleanup(os.environ.pop, "CC_TEST_PRODUCT_DB_HOST")

        manager = SessionManager(None, self.config_file, self.secrets_file)

        self.assertEqual(manager.get_product_default_connection(),
                         {"host": "env-db.test.org"})

    def test_reload_config(self):
        """Changed defaults are applied when the configuration is reloaded."""
        _write_json(self.config_file, _config({"engine": "sqlite"}))
        manager = SessionManager(None, self.config_file, self.secrets_file)
        self.assertEqual(manager.get_product_default_connection(),
                         {"engine": "sqlite"})

        _write_json(self.config_file,
                    _config({"engine": "postgresql", "port": 5433}))
        manager.reload_config()

        self.assertEqual(manager.get_product_default_connection(),
                         {"engine": "postgresql", "port": 5433})

    def test_returned_value_is_a_copy(self):
        """Modifying the returned value does not change the configuration."""
        _write_json(self.config_file, _config({"engine": "sqlite"}))
        manager = SessionManager(None, self.config_file, self.secrets_file)

        manager.get_product_default_connection()["engine"] = "postgresql"

        self.assertEqual(manager.get_product_default_connection(),
                         {"engine": "sqlite"})
