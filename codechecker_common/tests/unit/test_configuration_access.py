# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
from typing import cast

import unittest

from codechecker_common import configuration_access as cfg


class ConfigurationAccessTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.SimpleSchema = cfg.Schema()
        cls.SimpleSchema.add_option("default", "/default",
                                    supports_update=False)
        cls.SimpleSchema.add_option("writable", "/writable", read_only=False)
        cls.SimpleSchema.add_option("with_default_1", "/with_default_1",
                                    default=42, read_only=False)
        cls.SimpleSchema.add_option("with_default_2", "/with_default_2",
                                    default=lambda *_: 159, read_only=False)

        cls.SimpleSchema.add_option("validated", "/validated",
                                    validation_predicate=lambda v: v != 1,
                                    read_only=False,
                                    default=0)

        cls.ValidationCallbackTriggered = None

        def _validation_callback(_option, value):
            cls.ValidationCallbackTriggered = value

        cls.SimpleSchema.add_option(
            "validated_with_callback", "/validated_with_callback",
            validation_predicate=lambda v: v != 4,
            validation_fail_action=_validation_callback,
            read_only=False,
            default=0)

        cls.ComplexSchema = cfg.Schema()
        privilege_dir = cast(
            cfg.OptionDirectory,
            cls.ComplexSchema.add_option("privileges", "/privileges/"))
        privilege_dir.add_option("normal_privilege", "./normal_privilege")
        config_dir = cast(
            cfg.OptionDirectoryList,
            cls.ComplexSchema.add_option("configs", "/configs[]/"))
        config_dir.add_option("username", "./username",
                              validation_predicate=lambda v: v != "")
        config_dir.add_option("is_admin", "./is_admin", default=False,
                              validation_predicate=lambda v: type(v) is bool)

        cls.QuadraticSchema = cfg.Schema()
        cls.QuadraticSchema.add_option("users", "/Users[]/")
        cls.QuadraticSchema.add_option("username", "/Users[]/username",
                                       validation_predicate=lambda v: v != "")
        cls.QuadraticSchema.add_option("user_privileges",
                                       "/Users[]/Privileges[]/")
        cls.QuadraticSchema.add_option("user_privilege_code",
                                       "/Users[]/Privileges[]/ID",
                                       validation_predicate=lambda v:
                                       type(v) is int)
        cls.QuadraticSchema.add_option("user_privilege_scope",
                                       "/Users[]/Privileges[]/Scope",
                                       validation_predicate=lambda v:
                                       type(v) is list)

    def test_option_disallows_invalid_default(self):
        s = cfg.Schema()
        with self.assertRaises(ValueError):
            s.add_option("invalid", "/invalid",
                         default=42,
                         validation_predicate=lambda v: v != 42)

    def test_simple_options(self):
        c = cfg.Configuration.from_memory(self.SimpleSchema, {})

        with self.assertRaises(cfg.UnsetError):
            self.assertEqual(c.default, -1)
        with self.assertRaises(cfg.ReadOnlyOptionError):
            c.default = 8

        with self.assertRaises(cfg.UnsetError):
            self.assertEqual(c.writable, -1)

        c.writable = -2
        self.assertEqual(c.writable, -2)

        self.assertEqual(c.with_default_1, 42)
        self.assertEqual(c.with_default_2, 159)

        c.with_default_1 = 16
        self.assertEqual(c.with_default_1, 16)
        self.assertEqual(c.with_default_2, 159)

        c.with_default_2 = 42
        self.assertEqual(c.with_default_1, 16)
        self.assertEqual(c.with_default_2, 42)

        self.assertEqual(c.validated, 0)
        with self.assertRaises(cfg.InvalidOptionValueError):
            c.validated = 1
        self.assertEqual(c.validated, 0)
        c.validated = 2
        self.assertEqual(c.validated, 2)

    def test_simple_options_with_existing_info(self):
        c = cfg.Configuration.from_memory(
            self.SimpleSchema,
            {
                "default": 1,
                "writable": 2,
                "with_default_1": 999,
                "with_default_2": -42,
                "validated": 8
            })

        self.assertEqual(c.default, 1)
        self.assertEqual(c.writable, 2)
        self.assertEqual(c.with_default_1, 999)
        self.assertEqual(c.with_default_2, -42)
        self.assertEqual(c.validated, 8)

        c = cfg.Configuration.from_memory(
            self.SimpleSchema,
            {
                "validated": 1
            })

        with self.assertRaises(cfg.InvalidOptionValueError):
            self.assertEqual(c.validated, 1)

    def test_validation_callback(self):
        c = cfg.Configuration.from_memory(self.SimpleSchema, {})

        with self.assertRaises(cfg.InvalidOptionValueError):
            c.validated_with_callback = 4
        self.assertEqual(self.ValidationCallbackTriggered, 4)

    def test_early_validation(self):
        c = cfg.Configuration.from_memory(
            self.SimpleSchema,
            {
                # default is missing
                "writable": 42,
                # with_default_1 is missing
                "with_default_2": -42,
                # validated is failing
                "validated": 1,
                # validated_with_callback is failing
                "validated_with_callback": 4,
            })

        fails = c._validate()
        self.assertEqual(self.ValidationCallbackTriggered, 4)
        self.assertEqual(len(fails), 3)
        self.assertSetEqual(
            {"/default", "/validated", "/validated_with_callback"},
            set(dict(fails).keys()))

        # Missing entire keys that are "sub-directories" of values.
        c = cfg.Configuration.from_memory(self.ComplexSchema, {})

        fails = c._validate()
        self.assertEqual(len(fails), 1)
        self.assertSetEqual(
            {"/privileges/normal_privilege"},
            set(dict(fails).keys()))

        c = cfg.Configuration.from_memory(
            self.ComplexSchema,
            {
                "privileges": {
                    "normal_privilege": 1
                },
                "configs": [
                    {
                        "username": "",
                        "is_admin": False
                    },
                    {
                        "username": "admin",
                        "is_admin": True
                    },
                    {
                        "username": "user",
                        "is_admin": 3.14
                    }
                ]
            })

        fails = c._validate()
        self.assertEqual(len(fails), 2)
        self.assertSetEqual(
            {"/configs/0/username", "/configs/2/is_admin"},
            set(dict(fails).keys()))

        c = cfg.Configuration.from_memory(
            self.QuadraticSchema,
            {
                "Users": [
                    {
                        "username": "root",
                        "Privileges": [
                            {
                                "ID": 0,
                                "Scope": ""
                            }
                        ]
                    },
                    {
                        "username": "admin",
                        "Privileges": [
                            {
                                "ID": 42,
                                "Scope": ["normal"]
                            },
                            {
                                "ID": 43,
                                "Scope": ["secret", "confidential"]
                            }
                        ]
                    },
                    {
                        "username": "user",
                        "Privileges": [
                            {
                                "ID": None,
                                "Scope": ["nothing"]
                            }
                        ]
                    }
                ]
            })

        fails = c._validate()
        self.assertEqual(len(fails), 2)
        self.assertSetEqual(
            {"/Users/0/Privileges/0/Scope", "/Users/2/Privileges/0/ID"},
            set(dict(fails).keys()))

    def test_update(self):
        c1 = {"default": 1}
        c2 = {"default": 2}
        c = cfg.Configuration.from_memory(self.SimpleSchema, c1)
        changes, fails = c._update_from_memory(c2)

        self.assertEqual(len(changes), 0)
        self.assertEqual(len(fails), 1)
        self.assertDictEqual(
            {"/default":
             cfg.ConfigurationUpdateFailureReason.UPDATE_UNSUPPORTED},
            {path: reason for path, _, reason in fails})

        self.assertEqual(c.default, 1)

        c1 = {
                "Users": [
                    {
                        "username": "root",
                        "Privileges": [
                            {
                                "ID": 0,
                                "Scope": [""]
                            }
                        ]
                    },
                    {
                        "username": "admin",
                        "Privileges": [
                            {
                                "ID": 42,
                                "Scope": ["normal"]
                            },
                            {
                                "ID": 43,
                                "Scope": ["secret", "confidential"]
                            }
                        ]
                    },
                    {
                        "username": "user",
                        "Privileges": [
                            {
                                "ID": 1337,
                                "Scope": ["nothing"]
                            }
                        ]
                    }
                ]
            }
        c2 = {
                "Users": [
                    {
                        "username": "__root",
                        "Privileges": [
                            {
                                "ID": 1,
                                "Scope": [""]
                            }
                        ]
                    },
                    {
                        "username": "__admin",
                        "Privileges": [
                            {
                                "ID": 42,
                                "Scope": ["normal"]
                            },
                            {
                                "ID": 43,
                                "Scope": ["secret", "confidential"]
                            }
                        ]
                    },
                    {
                        "username": "?",  # This change is dropped...
                        "Privileges": [
                            {
                                "ID": None,  # ... because this is invalid.
                                "Scope": ["nothing"]
                            }
                        ]
                    }
                ]
            }
        c = cfg.Configuration.from_memory(self.QuadraticSchema, c1)
        changes, fails = c._update_from_memory(c2)

        self.assertEqual(len(changes), 3)
        self.assertSetEqual(
            {"/Users/0/username", "/Users/0/Privileges/0/ID",
             "/Users/1/username"},
            {path for path, _, _ in changes})

        self.assertEqual(len(fails), 3)
        self.assertDictEqual(
            {"/Users/2/Privileges/0/ID":
             cfg.ConfigurationUpdateFailureReason.VERIFICATION_FAILED,
             "/Users/2/Privileges/0": cfg.ConfigurationUpdateFailureReason.
             LIST_ELEMENT_ONLY_PARTIALLY_UPDATED,
             "/Users/2": cfg.ConfigurationUpdateFailureReason.
             LIST_ELEMENT_ONLY_PARTIALLY_UPDATED},
            {path: reason for path, _, reason in fails})

        self.assertEqual(cast(cfg.OptionDirectoryList._Access, c.Users)[2]
                         .username, "user")
