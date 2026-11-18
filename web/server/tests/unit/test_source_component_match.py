# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Regression tests for https://github.com/Ericsson/codechecker/issues/2564 -
a source component like '+*/myproj/a.cpp' followed by '-*' matched no files
at all, because every '-' rule overrode every '+' rule.

When a file matches both a '+' and a '-' rule, the more specific rule (the
one with more non-wildcard characters) decides. On a tie the '-' rule wins,
which keeps the behaviour introduced by PR #1715. The order of the rules
does not matter.

Both server code paths that assign files to components are checked:
'update_source_component_files()' (run when a component is added or
changed) and 'assign_file_to_source_components()' (run when a file is
stored).
"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from codechecker_server.api.mass_store_run import \
    assign_file_to_source_components
from codechecker_server.api.report_server import \
    update_source_component_files
from codechecker_server.database.run_db_model import \
    Base, File, SourceComponent, SourceComponentFile


FILES = [
    '/src/myproj/a.cpp',
    '/src/myproj/b.cpp',
    '/src/myproj/c.cpp',
    '/src/test_proj/x.cpp',
    '/src/test_files/y.cpp',
    '/src/other/z.cpp',
]

# Component value -> files expected to belong to the component.
CASES = {
    # Issue #2564: a specific include beats a catch-all exclude.
    'include one file, exclude everything else': (
        ['+*/myproj/a.cpp', '-*'],
        {'/src/myproj/a.cpp'}),
    # The order of the rules does not matter.
    'exclude everything else first, include one file': (
        ['-*', '+*/myproj/a.cpp'],
        {'/src/myproj/a.cpp'}),
    # PR #1715: a more specific exclude beats a broader include.
    'broad include, more specific exclude': (
        ['+*/test*', '-*/test_p*'],
        {'/src/test_files/y.cpp'}),
    'directory include, single file exclude': (
        ['+*/myproj/*', '-*/myproj/a.cpp'],
        {'/src/myproj/b.cpp', '/src/myproj/c.cpp'}),
    # Equally specific rules: the exclude wins.
    'tie goes to the exclude rule': (
        ['+*/myproj/a.cpp', '-*/myproj/a.cpp'],
        set()),
    'include only': (
        ['+*/myproj/*'],
        {'/src/myproj/a.cpp', '/src/myproj/b.cpp', '/src/myproj/c.cpp'}),
    'exclude only': (
        ['-*/myproj/*'],
        {'/src/test_proj/x.cpp', '/src/test_files/y.cpp',
         '/src/other/z.cpp'}),
}


class SourceComponentMatchTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            'sqlite:///:memory:',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def __add_files(self):
        """ Add every file of FILES and return them by path. """
        files = {}
        for path in FILES:
            f = File(path, 'hash_' + path, None, None)
            self.session.add(f)
            files[path] = f
        self.session.flush()
        return files

    def __add_component(self, name, rules):
        component = SourceComponent(name, '\n'.join(rules).encode('utf-8'))
        self.session.add(component)
        self.session.flush()
        return component

    def __component_files(self, name):
        """ Return the paths of the files assigned to the component. """
        rows = self.session.query(File.filepath) \
            .join(SourceComponentFile,
                  SourceComponentFile.file_id == File.id) \
            .filter(SourceComponentFile.source_component_name == name) \
            .all()
        return {row[0] for row in rows}

    def test_component_added_after_files_are_stored(self):
        """
        The files already exist when the component is created, so the file
        list is computed by 'update_source_component_files()'.
        """
        self.__add_files()
        for name, (rules, expected) in CASES.items():
            with self.subTest(name, rules=rules):
                component = self.__add_component(name, rules)
                update_source_component_files(self.session, component)
                self.assertEqual(self.__component_files(name), expected)

    def test_files_stored_after_component_is_added(self):
        """
        The component exists before the files are stored, so each file is
        assigned by 'assign_file_to_source_components()'.
        """
        for name, (rules, _) in CASES.items():
            self.__add_component(name, rules)

        for path, f in self.__add_files().items():
            assign_file_to_source_components(self.session, f.id, path)

        for name, (rules, expected) in CASES.items():
            with self.subTest(name, rules=rules):
                self.assertEqual(self.__component_files(name), expected)
