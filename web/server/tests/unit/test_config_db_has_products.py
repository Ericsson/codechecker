# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Regression tests for
https://github.com/Ericsson/codechecker/issues/1386 (and its duplicate,
https://github.com/Ericsson/codechecker/issues/3810) - starting the server
after 'Default.sqlite' was removed, while the config database still has
product(s) registered, must not attempt to (re-)create the initial
'Default' product.

Previously, whether to auto-create the 'Default' product was decided
purely from 'Default.sqlite' file's absence on disk:

    create_default_product = 'sqlite' in args and \\
                             not os.path.exists(default_product_path)

If that file was deleted while the config database still had product(s)
registered (the old 'Default' entry, or any other product), the server
would still try to create a new initial 'Default' product, which
'add_initial_run_database' explicitly refuses to do on a non-empty config
database - crashing the server on startup.
"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from codechecker_server.cli.server import config_db_has_products
from codechecker_server.database.config_db_model import Base, Product


class _FakeSqlServer:
    """
    Minimal stand-in for a 'codechecker_server.database.database.SQLServer'
    subclass, exposing only what 'config_db_has_products' actually uses.
    """

    def __init__(self, engine):
        self.__engine = engine

    def create_engine(self):
        return self.__engine


class ConfigDbHasProductsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.sql_server = _FakeSqlServer(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_empty_config_db_has_no_products(self):
        """
        A brand new, empty config database (e.g. on first-ever server
        start) must report that it has no products, so the initial
        'Default' product can still be auto-created.
        """
        self.assertFalse(config_db_has_products(self.sql_server))

    def test_config_db_with_existing_default_product(self):
        """
        This is the exact scenario from #1386/#3810: 'Default.sqlite' was
        deleted, but the config database still has the 'Default' product
        registered. The helper must report this as non-empty, so the
        caller knows not to attempt creating a new initial product.
        """
        session = sessionmaker(bind=self.engine)()
        session.add(Product(
            'Default', 'sqlite_step://Default.sqlite', 'Default',
            "Default product created at server start."))
        session.commit()
        session.close()

        self.assertTrue(config_db_has_products(self.sql_server))

    def test_config_db_with_unrelated_product(self):
        """
        Any registered product - not just one literally named 'Default' -
        must prevent auto-creation of a new initial 'Default' product.
        """
        session = sessionmaker(bind=self.engine)()
        session.add(Product(
            'my_project', 'postgresql://...', 'My Project', None))
        session.commit()
        session.close()

        self.assertTrue(config_db_has_products(self.sql_server))


if __name__ == "__main__":
    unittest.main()
