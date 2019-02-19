# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" Test the option parsing and filtering form the compilation commands. """
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import unittest

from codechecker.buildlog import log_parser
from codechecker.buildlog.build_action import BuildAction


class OptionParserTest(unittest.TestCase):
    """
    Test the option parser module which handles the
    parsing of the g++/gcc compiler options.
    """

    def test_build_onefile(self):
        """
        Test the build command of a simple file.
        """
        action = {
            'file': 'main.cpp',
            'command': "g++ -o main -fno-merge-const-bfstores main.cpp",
            'directory': ''}

        res = log_parser.parse_options(action)
        print(res)
        self.assertFalse("-fno-merge-const-bfstores" in res.analyzer_options)
        self.assertTrue('main.cpp' == res.source)
        self.assertTrue(BuildAction.COMPILE, res.action_type)
        self.assertEquals(0, len(res.analyzer_options))

    def test_build_multiplefiles(self):
        """
        Test the build command of multiple files.
        """
        action = {
            'file': 'main.cpp',
            'command': "g++ -o main main.cpp lib.cpp",
            'directory': ''}

        res = log_parser.parse_options(action)
        print(res)
        self.assertTrue('main.cpp' == res.source)
        self.assertEquals(BuildAction.COMPILE, res.action_type)

    def test_compile_onefile(self):
        """
        Test the compiler command of one file.
        """
        action = {
            'file': 'main.cpp',
            'command': "g++ -c main.cpp",
            'directory': ''}

        res = log_parser.parse_options(action)
        print(res)
        self.assertTrue('main.cpp' == res.source)
        self.assertEquals(BuildAction.COMPILE, res.action_type)

    def test_preprocess_onefile(self):
        """
        Test the preprocess command of one file.
        """
        action = {
            'file': 'main.c',
            'command': "gcc -E main.c",
            'directory': ''}

        res = log_parser.parse_options(action)
        print(res)

        self.assertTrue('main.c' == res.source)
        self.assertEqual(BuildAction.PREPROCESS, res.action_type)

    def test_compile_lang(self):
        """
        Test if the compilation language is
        detected correctly from the command line.
        """
        lang = 'c'
        action = {
            'file': 'main.c',
            'command': "gcc -c -x " + lang + ' main.c',
            'directory': ''}

        res = log_parser.parse_options(action)
        print(res)

        self.assertTrue('main.c' == res.source)
        self.assertEqual(lang, res.lang)
        self.assertEqual(BuildAction.COMPILE, res.action_type)

    def test_compile_arch(self):
        """
        Test if the compilation architecture is
        detected correctly from the command line.
        """
        arch = 'x86_64'
        action = {
            'file': 'main.c',
            'command': "gcc -c -arch " + arch + ' main.c',
            'directory': ''
        }

        res = log_parser.parse_options(action)
        print(res)

        self.assertTrue('main.c' == res.source)
        self.assertEqual(arch, res.target)
        self.assertEqual(BuildAction.COMPILE, res.action_type)

    def test_compile_optimized(self):
        """
        Test if the compilation arguments is
        detected correctly from the command line.
        """
        source_files = ["main.cpp"]
        compiler_options = ["-O3"]
        build_cmd = "g++ -c " + \
                    ' '.join(compiler_options) + ' ' + \
                    ' '.join(source_files)
        action = {
            'file': 'main.cpp',
            'command': build_cmd,
            'directory': ''}

        res = log_parser.parse_options(action)
        print(res)
        self.assertTrue(set(compiler_options) == set(res.analyzer_options))
        self.assertEqual(BuildAction.COMPILE, res.action_type)

    def test_compile_with_include_paths(self):
        """
        sysroot should be detected as compiler option because it is needed
        for the analyzer too to search for headers.
        """
        source_files = ["main.cpp", "test.cpp"]
        compiler_options = ["-std=c++11",
                            "-include/include/myheader.h",
                            "-include", "/include/myheader2.h",
                            "--include", "/include/myheader3.h",
                            "--sysroot", "/home/sysroot",
                            "--sysroot=/home/sysroot3",
                            "-isysroot", "/home/isysroot",
                            "-isysroot/home/isysroot2",
                            "-I/home/test", "-I", "/home/test2",
                            "-idirafter", "/dirafter1",
                            "-idirafter/dirafter2"]
        linker_options = ["-L/home/test_lib", "-lm"]
        build_cmd = "g++ -o myapp " + \
                    ' '.join(compiler_options) + ' ' + \
                    ' '.join(linker_options) + ' ' + \
                    ' '.join(source_files)
        action = {
            'file': 'main.cpp',
            'command': build_cmd,
            'directory': ''}

        res = log_parser.parse_options(action)
        print(res)
        print(compiler_options)
        print(res.analyzer_options)
        self.assertTrue('main.cpp' == res.source)
        self.assertTrue(set(compiler_options) == set(res.analyzer_options))
        self.assertEqual(BuildAction.COMPILE, res.action_type)

    def test_link_only_multiple_files(self):
        """
        Should be link if only object files are in the command.
        """
        build_cmd = "g++ -o fubar foo.o main.o bar.o -lm"
        action = {
            'file': '',
            'command': 'g++ -o fubar foo.o main.o bar.o -m',
            'directory': ''}
        res = log_parser.parse_options(action)
        print(res)
        self.assertEquals(BuildAction.LINK, res.action_type)

    def test_link_with_include_paths(self):
        """
        Should be link if only object files are in the command.
        """
        object_files = ["foo.o",
                        "main.o",
                        "bar.o"]
        compiler_options = ["--sysroot", "/home/sysroot",
                            "-isysroot/home/isysroot",
                            "-I/home/test"]
        linker_options = ["-L/home/test_lib", "-lm"]
        build_cmd = "g++ -o fubar " + \
                    ' '.join(compiler_options) + ' ' + \
                    ' '.join(linker_options) + ' ' + \
                    ' '.join(object_files)
        action = {
            'file': '',
            'command': build_cmd,
            'directory': ''}

        res = log_parser.parse_options(action)
        print(res)
        self.assertTrue('' == res.source)
        self.assertTrue(set(compiler_options) == set(res.analyzer_options))
        self.assertEqual(BuildAction.LINK, res.action_type)

    def test_ignore_flags(self):
        """
        Test if special compiler options are ignored properly.
        """
        ignore = ["-Werror", "-MT hello", "-M", "-fsyntax-only",
                  "-mfloat-gprs=double", "-mfloat-gprs=yes",
                  "-mabi=spe", "-mabi=eabi",
                  '-Xclang', '-mllvm',
                  '-Xclang', '-instcombine-lower-dbg-declare=0']
        build_cmd = "g++ {} main.cpp".format(' '.join(ignore))
        action = {
            'file': 'main.cpp',
            'command': build_cmd,
            'directory': ''}
        res = log_parser.parse_options(action)
        self.assertEqual(res.analyzer_options, ["-fsyntax-only"])

    def test_preserve_flags(self):
        """
        Test if special compiler options are preserved properly.
        """
        preserve = ['-nostdinc', '-nostdinc++', '-pedantic']
        action = {
            'file': 'main.cpp',
            'command': "g++ {} main.cpp".format(' '.join(preserve)),
            'directory': ''}
        res = log_parser.parse_options(action)
        self.assertEqual(res.analyzer_options, preserve)

    def test_compiler_toolchain(self):
        """
        Test if compiler toolchain is parsed and forwarded properly.
        """
        source_files = ["main.cpp"]
        compiler_options = ["--gcc-toolchain=/home/user/mygcctoolchain"]
        build_cmd = "g++ -c " + \
                    ' '.join(compiler_options) + ' ' + \
                    ' '.join(source_files)
        action = {
            'file': 'main.cpp',
            'command': build_cmd,
            'directory': ''}

        res = log_parser.parse_options(action)
        print(res)
        self.assertTrue(set(compiler_options) == set(res.analyzer_options))
        self.assertEqual(BuildAction.COMPILE, res.action_type)

    def test_ccache_compiler(self):
        action = {
            'file': 'main.cpp',
            'directory': ''}

        action['command'] = 'ccache g++ main.cpp'
        res = log_parser.parse_options(action)
        self.assertEqual(res.original_command, 'ccache g++ main.cpp')

        action['command'] = 'ccache main.cpp'
        res = log_parser.parse_options(action)
        self.assertEqual(res.original_command, 'ccache main.cpp')

        action['command'] = 'ccache -Ihello main.cpp'
        res = log_parser.parse_options(action)
        self.assertEqual(res.original_command, 'ccache -Ihello main.cpp')
