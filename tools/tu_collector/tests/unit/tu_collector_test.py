# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
The TU collector collects the files which constitute the translation unit.
These files are compressed in a .zip file. This test intends to check if the
.zip file contains some files which are required to be there for sure.
"""


import inspect
import json
import os
import shlex
import shutil
import tempfile
import unittest
import zipfile
from unittest import mock

from tu_collector import tu_collector


class TUCollectorTest(unittest.TestCase):
    def setUp(self):
        self._test_proj_dir = os.path.abspath(os.environ['TEST_PROJ'])

        compile_json = os.path.join(self._test_proj_dir,
                                    'compile_command.json')

        with open(compile_json, mode='rb') as cmpjson:
            self.compile_cmd_data = json.load(cmpjson)

        # Overwrite the directory paths.
        # This is needed because the tests run on different machines
        # so the directory path changes in each case.
        for cmp in self.compile_cmd_data:
            cmp['directory'] = self._test_proj_dir

    def test_file_existence(self):
        zip_file_name = tempfile.mkstemp(suffix='.zip')[1]
        tu_collector.zip_tu_files(zip_file_name, self.compile_cmd_data)

        with zipfile.ZipFile(zip_file_name) as archive:
            files = archive.namelist()

        os.remove(zip_file_name)

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'main.c')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'main.cpp')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'vector')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'hello.c')) for path in files]))

        self.assertIn('compilation_database.json', files)

    def test_ctu_collection(self):
        with tempfile.TemporaryDirectory() as ctu_deps_dir:
            ctu_action = next(filter(lambda ba: ba['file'] == 'ctu.cpp',
                                     self.compile_cmd_data))

            hash_fun = dict(
                inspect.getmembers(tu_collector))['__analyzer_action_hash']

            with open(os.path.join(ctu_deps_dir, hash_fun(ctu_action)), 'w') \
                    as f:
                f.write(os.path.join(self._test_proj_dir, 'zero.cpp'))

            with tempfile.NamedTemporaryFile(suffix='.zip') as zip_file:
                tu_collector.zip_tu_files(zip_file.name, self.compile_cmd_data,
                                          file_filter='ctu.cpp',
                                          ctu_deps_dir=ctu_deps_dir)

                with zipfile.ZipFile(zip_file.name) as archive:
                    files = archive.namelist()

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'vector')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'ctu.cpp')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'zero.cpp')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'zero.h')) for path in files]))

    @unittest.skipUnless(shutil.which('gcc') and shutil.which('clang'),
                         'GCC and Clang are required for this regression test')
    def test_gcc_build_collects_clang_only_header(self):
        """Issue #3161: a Clang reproducer needs Clang-only dependencies."""
        with tempfile.TemporaryDirectory() as build_dir:
            source = os.path.join(build_dir, 'source.c')
            gcc_header = os.path.join(build_dir, 'gcc_only.h')
            clang_header = os.path.join(build_dir, 'clang_only.h')

            with open(source, 'w', encoding='utf-8') as output:
                output.write('#if defined(__GNUC__) && !defined(__clang__)\n'
                             '#include "gcc_only.h"\n'
                             '#endif\n'
                             '#ifdef __clang__\n'
                             '#include "clang_only.h"\n'
                             '#endif\n')
            for header in (gcc_header, clang_header):
                with open(header, 'w', encoding='utf-8') as output:
                    output.write('/* Synthetic dependency. */\n')

            gcc_command = f"{shlex.quote(shutil.which('gcc'))} -c source.c"
            clang_command = f"{shlex.quote(shutil.which('clang'))} -c source.c"
            check_output = tu_collector.subprocess.check_output

            def bounded_check_output(*args, **kwargs):
                kwargs['timeout'] = 10
                return check_output(*args, **kwargs)

            with mock.patch.object(tu_collector.subprocess, 'check_output',
                                   side_effect=bounded_check_output):
                gcc_files, gcc_error = tu_collector.get_dependent_headers(
                    gcc_command, build_dir)
                clang_files, clang_error = tu_collector.get_dependent_headers(
                    clang_command, build_dir)

                self.assertFalse(gcc_error)
                self.assertFalse(clang_error)
                self.assertIn(gcc_header, gcc_files)
                self.assertNotIn(clang_header, gcc_files)
                self.assertIn(clang_header, clang_files)
                self.assertNotIn(gcc_header, clang_files)

                archive_path = os.path.join(build_dir, 'reproducer.zip')
                tu_collector.zip_tu_files(archive_path, [{
                    'file': 'source.c',
                    'command': gcc_command,
                    'directory': build_dir,
                }], dependency_commands=[[
                    shutil.which('clang'), '-x', 'c', 'source.c']])

            with zipfile.ZipFile(archive_path) as archive:
                archived_files = archive.namelist()
                stored_command = json.loads(archive.read(
                    'compilation_database.json'))[0]['command']

            self.assertEqual(stored_command, gcc_command)
            self.assertIn(os.path.join('sources-root', source.lstrip(os.sep)),
                          archived_files)
            self.assertIn(os.path.join('sources-root',
                                       clang_header.lstrip(os.sep)),
                          archived_files)

    @unittest.skipUnless(shutil.which('g++') and shutil.which('clang'),
                         'G++ and Clang are required')
    def test_gpp_build_uses_clang_cpp_mode_for_dependencies(self):
        """A G++ build command must scan dependencies in Clang C++ mode."""
        with tempfile.TemporaryDirectory() as build_dir:
            source = os.path.join(build_dir, 'source.cpp')
            clang_header = os.path.join(build_dir, 'clang_only.hpp')
            with open(source, 'w', encoding='utf-8') as output:
                output.write('#if defined(__clang__) && defined(__cplusplus)\n'
                             '#include "clang_only.hpp"\n'
                             '#endif\n')
            with open(clang_header, 'w', encoding='utf-8') as output:
                output.write('/* Synthetic C++ dependency. */\n')

            command = f"{shlex.quote(shutil.which('g++'))} -c source.cpp"
            check_output = tu_collector.subprocess.check_output
            used_compilers = []

            def bounded_check_output(args, **kwargs):
                used_compilers.append(args[0])
                kwargs['timeout'] = 10
                return check_output(args, **kwargs)

            archive_path = os.path.join(build_dir, 'reproducer.zip')
            with mock.patch.object(tu_collector.subprocess, 'check_output',
                                   side_effect=bounded_check_output):
                tu_collector.zip_tu_files(archive_path, [{
                    'file': 'source.cpp',
                    'command': command,
                    'directory': build_dir,
                }], dependency_commands=[[
                    shutil.which('clang'), '-x', 'c++', 'source.cpp']])

            with zipfile.ZipFile(archive_path) as archive:
                archived_files = archive.namelist()
                stored_command = json.loads(archive.read(
                    'compilation_database.json'))[0]['command']

            self.assertIn(os.path.join('sources-root',
                                       clang_header.lstrip(os.sep)),
                          archived_files)
            self.assertEqual(stored_command, command)
            self.assertEqual(used_compilers, [shutil.which('clang')])

    @unittest.skipUnless(shutil.which('clang'), 'Clang is required')
    def test_dependency_commands_follow_actions_after_ctu_filtering(self):
        """CTU expansion must not pair commands with reordered actions."""
        with tempfile.TemporaryDirectory() as root:
            actions = []
            for name in ('a', 'b'):
                build_dir = os.path.join(root, name)
                os.mkdir(build_dir)
                with open(os.path.join(build_dir, name + '.c'), 'w',
                          encoding='utf-8') as output:
                    output.write(f'#include "{name}.h"\n')
                with open(os.path.join(build_dir, name + '.h'), 'w',
                          encoding='utf-8') as output:
                    output.write('/* Synthetic dependency. */\n')
                actions.append({
                    'file': name + '.c',
                    'command': f'gcc -c {name}.c',
                    'directory': build_dir,
                })

            ctu_dir = os.path.join(root, 'ctu')
            os.mkdir(ctu_dir)
            hash_fun = dict(inspect.getmembers(tu_collector))[
                '__analyzer_action_hash']
            with open(os.path.join(ctu_dir, hash_fun(actions[1])), 'w',
                      encoding='utf-8') as output:
                output.write(os.path.join(actions[0]['directory'], 'a.c'))

            dependency_commands = [
                [shutil.which('clang'), '-x', 'c', name + '.c']
                for name in ('a', 'b')]
            check_output = tu_collector.subprocess.check_output

            def bounded_check_output(*args, **kwargs):
                kwargs['timeout'] = 10
                return check_output(*args, **kwargs)

            archive_path = os.path.join(root, 'reproducer.zip')
            with mock.patch.object(tu_collector.subprocess, 'check_output',
                                   side_effect=bounded_check_output):
                tu_collector.zip_tu_files(
                    archive_path, actions, file_filter='b.c',
                    ctu_deps_dir=ctu_dir,
                    dependency_commands=dependency_commands)

            with zipfile.ZipFile(archive_path) as archive:
                archived_files = archive.namelist()

            self.assertNotIn('no-sources', archived_files)
            for name, action in zip(('a', 'b'), actions):
                self.assertIn(os.path.join(
                    'sources-root', action['directory'].lstrip(os.sep),
                    name + '.h'), archived_files)
