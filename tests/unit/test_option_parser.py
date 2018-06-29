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

from libcodechecker.log import option_parser
from libcodechecker.log.option_parser import ActionType


class OptionParserTest(unittest.TestCase):
    """
    Test the option parser module which handles the
    parsing of the g++/gcc compiler options.
    """

    def test_build_onefile(self):
        """
        Test the build command of a simple file.
        """
        source_files = ["main.cpp"]
        build_cmd = "g++ -o main -fno-merge-const-bfstores " +\
                    ' '.join(source_files)

        res = option_parser.parse_options(build_cmd)
        print(res)
        self.assertFalse("-fno-merge-const-bfstores" in res.compile_opts)
        self.assertTrue(set(source_files) == set(res.files))
        self.assertTrue(ActionType.COMPILE, res.action)
        self.assertEquals(0, len(res.compile_opts))

    def test_build_multiplefiles(self):
        """
        Test the build command of multiple files.
        """
        source_files = ["lib.cpp", "main.cpp"]
        build_cmd = "g++ -o main " + ' '.join(source_files)

        res = option_parser.parse_options(build_cmd)
        print(res)
        self.assertTrue(set(source_files) == set(res.files))
        self.assertEquals(ActionType.COMPILE, res.action)

    def test_compile_onefile(self):
        """
        Test the compiler command of one file.
        """
        source_files = ["main.cpp"]
        build_cmd = "g++ -c " + ' '.join(source_files)

        res = option_parser.parse_options(build_cmd)
        print(res)
        self.assertTrue(set(source_files) == set(res.files))
        self.assertEquals(ActionType.COMPILE, res.action)

    def test_preprocess_onefile(self):
        """
        Test the preprocess command of one file.
        """
        source_files = ["main.c"]
        build_cmd = "gcc -E " + ' '.join(source_files)

        print(build_cmd)
        res = option_parser.parse_options(build_cmd)
        print(res)

        self.assertTrue(set(source_files) == set(res.files))
        self.assertEqual(ActionType.PREPROCESS, res.action)

    def test_compile_lang(self):
        """
        Test if the compilation language is
        detected correctly from the command line.
        """
        source_files = ["main.c"]
        lang = 'c'
        build_cmd = "gcc -c -x " + lang + " " + ' '.join(source_files)

        print(build_cmd)
        res = option_parser.parse_options(build_cmd)
        print(res)

        self.assertTrue(set(source_files) == set(res.files))
        self.assertEqual(lang, res.lang)
        self.assertEqual(ActionType.COMPILE, res.action)

    def test_compile_arch(self):
        """
        Test if the compilation architecture is
        detected correctly from the command line.
        """
        source_files = ["main.c"]
        arch = 'x86_64'
        build_cmd = "gcc -c -arch " + arch + " " + ' '.join(source_files)

        print(build_cmd)
        res = option_parser.parse_options(build_cmd)
        print(res)

        self.assertTrue(set(source_files) == set(res.files))
        self.assertEqual(arch, res.arch)
        self.assertEqual(ActionType.COMPILE, res.action)

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

        res = option_parser.parse_options(build_cmd)
        print(res)
        self.assertTrue(set(compiler_options) == set(res.compile_opts))
        self.assertEqual(ActionType.COMPILE, res.action)

    def test_compile_with_include_paths(self):
        """
        sysroot should be detected as compiler option because it is needed
        for the analyzer too to search for headers.
        """
        source_files = ["main.cpp", "test.cpp"]
        compiler_options = ["-std=c++11",
                            "-include/include/myheader.h",
                            "-include /include/myheader2.h",
                            "--include", "/include/myheader3.h",
                            "--sysroot", "/home/sysroot",
                            "--sysroot=/home/sysroot3",
                            "-isysroot /home/isysroot",
                            "-isysroot/home/isysroot2",
                            "-I/home/test", "-I /home/test2",
                            "-idirafter /dirafter1",
                            "-idirafter/dirafter2"]
        linker_options = ["-L/home/test_lib", "-lm"]
        build_cmd = "g++ -o myapp " + \
                    ' '.join(compiler_options) + ' ' + \
                    ' '.join(linker_options) + ' ' + \
                    ' '.join(source_files)

        res = option_parser.parse_options(build_cmd)
        print(res)
        co_no_space = []
        for c in compiler_options:
            co_no_space.append(c.replace(" ", ""))
        print(set(co_no_space))
        print(set(res.compile_opts))
        self.assertTrue(set(source_files) == set(res.files))
        self.assertTrue(set(co_no_space) == set(res.compile_opts))
        self.assertTrue(set(linker_options) == set(res.link_opts))
        self.assertEqual(ActionType.COMPILE, res.action)

    def test_link_only_multiple_files(self):
        """
        Should be link if only object files are in the command.
        """
        build_cmd = "g++ -o fubar foo.o main.o bar.o -lm"
        res = option_parser.parse_options(build_cmd)
        print(res)
        self.assertEquals(ActionType.LINK, res.action)

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

        res = option_parser.parse_options(build_cmd)
        print(res)
        self.assertTrue(set(object_files) == set(res.files))
        self.assertTrue(set(compiler_options) == set(res.compile_opts))
        self.assertTrue(set(linker_options) == set(res.link_opts))
        self.assertEqual(ActionType.LINK, res.action)

    def test_ignore_flags(self):
        ignore = ["-Werror", "-MT hello", "-M", "-fsyntax-only",
                  "-mfloat-gprs=double", "-mfloat-gprs=yes"]
        build_cmd = "g++ {} main.cpp".format(' '.join(ignore))
        res = option_parser.parse_options(build_cmd)
        self.assertEqual(res.compile_opts, ["-fsyntax-only"])

    def test_compiler_toolchain(self):
        """
        Test if compiler toolchain is parsed and forwarded properly.
        """
        source_files = ["main.cpp"]
        compiler_options = ["--gcc-toolchain=/home/user/mygcctoolchain"]
        build_cmd = "g++ -c " + \
                    ' '.join(compiler_options) + ' ' + \
                    ' '.join(source_files)

        res = option_parser.parse_options(build_cmd)
        print(res)
        self.assertTrue(set(compiler_options) == set(res.compile_opts))
        self.assertEqual(ActionType.COMPILE, res.action)
