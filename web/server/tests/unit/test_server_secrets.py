# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Unit tests for resolving secrets and environment variables in the server
configuration file (``$SECRET:NAME$`` and ``$ENV:NAME$`` placeholders).

These tests exercise ``SessionManager.__get_config_dict()`` through the public
``SessionManager`` constructor. The constructor stores but never calls the
``config_db_sessionmaker`` during initialization, so ``None`` is passed for it.
The only structural requirement of the constructor is that the resolved
configuration contains an ``authentication`` section.
"""


import json
import os
import stat
import tempfile
import unittest
from unittest.mock import patch

from codechecker_server.session_manager import SessionManager


def _write_json(path, data):
    """Write ``data`` as JSON to ``path`` and restrict permissions to 0600."""
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def _write_raw(path, text):
    """Write raw ``text`` to ``path`` and restrict permissions to 0600."""
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


class ServerSecretsTest(unittest.TestCase):
    """
    Testing the secret/environment variable resolution of the server
    configuration file.
    """

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)

        self.config_file = os.path.join(self._tmp_dir.name,
                                        'server_config.json')
        self.secrets_file = os.path.join(self._tmp_dir.name,
                                         'server_secrets.json')

    def _build_manager(self, config, secrets=None):
        """
        Write the given ``config`` (and optionally ``secrets``) to disk and
        build a ``SessionManager`` from them, returning the resolved
        configuration dictionary (``scfg_dict``).
        """
        _write_json(self.config_file, config)
        if secrets is not None:
            _write_json(self.secrets_file, secrets)

        manager = SessionManager(None, self.config_file, self.secrets_file)
        return manager.scfg_dict

    def test_secret_resolved_from_secrets_file(self):
        """A ``$SECRET:NAME$`` value is replaced by the secrets file value."""
        config = {
            "authentication": {"enabled": False},
            "some_password": "$SECRET:DB_PASSWORD$"
        }
        secrets = {"DB_PASSWORD": "s3cr3t"}

        resolved = self._build_manager(config, secrets)

        self.assertEqual(resolved["some_password"], "s3cr3t")

    def test_env_variable_resolved(self):
        """A ``$ENV:NAME$`` value is replaced by the environment variable."""
        config = {
            "authentication": {"enabled": False},
            "some_password": "$ENV:CC_TEST_SECRET$"
        }

        with patch.dict(os.environ, {"CC_TEST_SECRET": "from-env"}):
            resolved = self._build_manager(config)

        self.assertEqual(resolved["some_password"], "from-env")

    def test_secret_can_be_arbitrary_json(self):
        """
        A secret value may be an arbitrary JSON structure (e.g. a dict), not
        just a string; it is substituted wholesale. This behaviour is
        intentional per the feature's design discussion.
        """
        auth_dict = {
            "enabled": True,
            "auths": ["cc:admin", "john:doe"],
            "groups": {"admin": ["cc"]}
        }
        config = {
            "authentication": {"enabled": False},
            "method_dictionary": "$SECRET:AUTH_DICT$"
        }
        secrets = {"AUTH_DICT": auth_dict}

        resolved = self._build_manager(config, secrets)

        self.assertEqual(resolved["method_dictionary"], auth_dict)

    def test_nested_dict_and_list_resolution(self):
        """Placeholders nested inside dicts and lists are all resolved."""
        config = {
            "authentication": {"enabled": False},
            "nested": {
                "inner_secret": "$SECRET:INNER$",
                "items": ["plain", "$SECRET:LIST_ITEM$", "$ENV:CC_ENV_ITEM$"]
            }
        }
        secrets = {"INNER": "inner-value", "LIST_ITEM": "list-value"}

        with patch.dict(os.environ, {"CC_ENV_ITEM": "env-item"}):
            resolved = self._build_manager(config, secrets)

        self.assertEqual(resolved["nested"]["inner_secret"], "inner-value")
        self.assertEqual(
            resolved["nested"]["items"],
            ["plain", "list-value", "env-item"])

    def test_inline_plaintext_is_backward_compatible(self):
        """
        Values without placeholders (inline plaintext secrets) are passed
        through unchanged, preserving backward compatibility.
        """
        config = {
            "authentication": {"enabled": False},
            "some_password": "plaintext-password"
        }

        resolved = self._build_manager(config)

        self.assertEqual(resolved["some_password"], "plaintext-password")

    def test_missing_secret_raises(self):
        """An unknown ``$SECRET:NAME$`` raises ValueError with the name."""
        config = {
            "authentication": {"enabled": False},
            "some_password": "$SECRET:MISSING$"
        }
        secrets = {"OTHER": "value"}

        with self.assertRaises(ValueError) as ctx:
            self._build_manager(config, secrets)

        self.assertIn("$SECRET:MISSING$", str(ctx.exception))
        self.assertIn("could not be resolved", str(ctx.exception))

    def test_missing_env_variable_raises(self):
        """An unknown ``$ENV:NAME$`` raises ValueError with the name."""
        config = {
            "authentication": {"enabled": False},
            "some_password": "$ENV:CC_DEFINITELY_MISSING$"
        }

        env_without = {
            k: v for k, v in os.environ.items()
            if k != "CC_DEFINITELY_MISSING"
        }
        with patch.dict(os.environ, env_without, clear=True):
            with self.assertRaises(ValueError) as ctx:
                self._build_manager(config)

        self.assertIn("$ENV:CC_DEFINITELY_MISSING$", str(ctx.exception))
        self.assertIn("could not be resolved", str(ctx.exception))

    def test_secret_used_but_secrets_file_missing_logs_error(self):
        """
        Using a ``$SECRET:NAME$`` while the secrets file does not exist raises
        ValueError and logs an explanatory error about the missing file.
        """
        config = {
            "authentication": {"enabled": False},
            "some_password": "$SECRET:DB_PASSWORD$"
        }
        # Note: no secrets file is written, so self.secrets_file is absent.
        _write_json(self.config_file, config)
        self.assertFalse(os.path.exists(self.secrets_file))

        with self.assertLogs(logger="server", level="ERROR") as log_ctx:
            with self.assertRaises(ValueError):
                SessionManager(None, self.config_file, self.secrets_file)

        joined = "\n".join(log_ctx.output)
        self.assertIn(self.secrets_file, joined)
        self.assertIn("does not exist", joined)

    def test_placeholder_not_anchored_is_left_literal(self):
        """
        The resolution regex is fully anchored, so a placeholder embedded in a
        larger string (e.g. ``prefix $SECRET:X$ suffix``) is NOT resolved and
        is kept as a literal. This documents the current behaviour so a future
        regex change is caught.
        """
        config = {
            "authentication": {"enabled": False},
            "some_password": "prefix $SECRET:DB_PASSWORD$ suffix"
        }
        secrets = {"DB_PASSWORD": "s3cr3t"}

        resolved = self._build_manager(config, secrets)

        self.assertEqual(
            resolved["some_password"],
            "prefix $SECRET:DB_PASSWORD$ suffix")

    def test_invalid_config_file_raises(self):
        """An invalid/empty configuration file raises ValueError."""
        _write_raw(self.config_file, "this is not valid json {")

        with self.assertRaises(ValueError) as ctx:
            SessionManager(None, self.config_file, self.secrets_file)

        self.assertIn("invalid", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
