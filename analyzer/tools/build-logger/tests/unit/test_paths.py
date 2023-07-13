#!/usr/bin/env python3

import glob
import os
import shutil
import tempfile
from typing import Mapping
from . import BasicLoggerTest, empty_env, REPO_ROOT

AVAILABLE_GNU_COMPILERS = [
    compiler
    for path in os.getenv("PATH").split(":")
    for compiler in glob.glob(f"{path}/g++-*")
]


def append_host_LD_LIBRARY_PATH(env: Mapping[str, str]) -> Mapping[str, str]:
    LD_LIBRARY_PATH = os.getenv("LD_LIBRARY_PATH")
    if LD_LIBRARY_PATH:
        if "LD_LIBRARY_PATH" not in env:
            env["LD_LIBRARY_PATH"] = ""
        env["LD_LIBRARY_PATH"] += ':' + LD_LIBRARY_PATH
    return env


class EscapingTests(BasicLoggerTest):
    def test_compiler_path1(self):
        """
        Test if the ld-logger recognizes compilers with the 'g++-' prefix.
        It will use the compilers available in the PATH matching that pattern.
        """
        if not AVAILABLE_GNU_COMPILERS:
            self.skipTest(
                f"No compiler matches the 'g++-*' pattern in your PATH"
            )

        for cc in AVAILABLE_GNU_COMPILERS:
            self.tearDown()  # Cleanup the previous iteration.
            self.setUp()
            logger_env = self.get_envvars()
            logger_env["CC_LOGGER_GCC_LIKE"] = "g++-"
            file = self.source_file
            binary = self.binary_file
            self.assume_successful_command(
                [cc, file, "-Werror", "-o", binary], logger_env
            )
            self.assume_successful_command(
                [binary], env=empty_env, outs="--VARIABLE--"
            )
            self.assert_json(
                command=f"{cc} {file} -Werror -o {binary}",
                file=file,
            )

    def test_compiler_path2(self):
        """
        Same as test_compiler_path1, but this time it uses the '/g++-'
        prefix, which (probably) shouldn't match to any compiler.
        """
        if not AVAILABLE_GNU_COMPILERS:
            self.skipTest(
                f"No compiler matches the 'g++-*' pattern in your PATH"
            )

        for cc in AVAILABLE_GNU_COMPILERS:
            self.tearDown()  # Cleanup the previous iteration.
            self.setUp()
            logger_env = self.get_envvars()
            logger_env["CC_LOGGER_GCC_LIKE"] = "/g++-"  # Extra forward slash!
            file = self.source_file
            binary = self.binary_file
            self.assume_successful_command(
                [cc, file, "-Werror", "-o", binary], logger_env
            )
            self.assume_successful_command(
                [binary], env=empty_env, outs="--VARIABLE--"
            )
            actual_json = self.read_actual_json()
            self.assertEqual(actual_json, "[\n]")

    def test_simple(self):
        """The most simple case: just compile a single file."""
        logger_env = self.get_envvars()
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            ["g++", file, "-Werror", "-o", binary], logger_env
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--VARIABLE--"
        )
        self.assert_json(
            command=f"g++ {file} -Werror -o {binary}",
            file=file,
        )

    def test_cpath(self):
        """
        Test if the content of the CPATH envvar is placed into the log file.
        """
        logger_env = self.get_envvars()
        logger_env["CPATH"] = "path1"
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            ["g++", file, "-Werror", "-o", binary], logger_env
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--VARIABLE--"
        )
        self.assert_json(
            command=f"g++ -I path1 {file} -Werror -o {binary}",
            file=file,
        )

    def test_cpath_after_last_I(self):
        """
        Test if the CPATH envvar holds multiple paths and
        they get put after the last specified include.
        """
        logger_env = self.get_envvars()
        logger_env["CPATH"] = ":path1:path2:"
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            [
                "g++",
                "-I",
                "p0",
                file,
                "-Werror",
                "-o",
                binary,
                "-I",
                "p1",
                "-I",
                "p2",
            ],
            logger_env,
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--VARIABLE--"
        )
        self.assert_json(
            command=f"g++ -I p0 {file} -Werror -o {binary} -I p1 "
                    f"-I p2 -I . -I path1 -I path2 -I .",
            file=file,
        )

    def test_cplus(self):
        """
        Test if compiling a C++ file, the CPLUS_INCLUDE_PATH
        gets put into the log file.
        """
        logger_env = self.get_envvars()
        logger_env["CPLUS_INCLUDE_PATH"] = "path1:path2"
        logger_env["C_INCLUDE_PATH"] = "path3:path4"
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            [
                "g++",
                "-I",
                "p0",
                "-isystem",
                "p1",
                file,
                "-Werror",
                "-o",
                binary,
            ],
            logger_env,
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--VARIABLE--"
        )
        self.assert_json(
            command=f"g++ -I p0 -isystem p1 -isystem path1 -isystem "
                    f"path2 {file} -Werror -o {binary}",
            file=file,
        )

    def test_c(self):
        """
        Test if compiling a C file, the C_INCLUDE_PATH
        gets put into the log file.
        """
        logger_env = self.get_envvars()
        logger_env["CPLUS_INCLUDE_PATH"] = "path1:path2"
        logger_env["C_INCLUDE_PATH"] = "path3:path4"
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            [
                "gcc",
                "-I",
                "p0",
                "-isystem",
                "p1",
                file,
                "-Werror",
                "-o",
                binary,
            ],
            logger_env,
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--VARIABLE--"
        )
        self.assert_json(
            command=f"gcc -I p0 -isystem p1 -isystem path3 -isystem "
                    f"path4 {file} -Werror -o {binary}",
            file=file,
        )

    def test_cpp(self):
        """
        Same as test_cplus(), but it uses the '-x c++' flag for
        explicitly stating the language of the file.
        """
        logger_env = self.get_envvars()
        logger_env["CPLUS_INCLUDE_PATH"] = "path1:path2"
        logger_env["C_INCLUDE_PATH"] = "path3:path4"
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            [
                "gcc",
                "-I",
                "p0",
                "-isystem",
                "p1",
                "-x",
                "c++",
                file,
                "-Werror",
                "-o",
                binary,
            ],
            logger_env,
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--VARIABLE--"
        )
        self.assert_json(
            command=f"gcc -I p0 -isystem p1 -isystem path1 -isystem "
                    f"path2 -x c++ {file} -Werror -o {binary}",
            file=file,
        )

    def test_response_file(self):
        """Test clang-specific response files."""
        logger_env = self.get_envvars()
        # clang might need Z3
        logger_env = append_host_LD_LIBRARY_PATH(logger_env)
        file = self.source_file
        binary = self.binary_file
        clang = shutil.which("clang")
        if not clang:
            self.skipTest(
                f"No compiler matches the 'clang' pattern in your PATH"
            )

        fd, rsp_file = tempfile.mkstemp(
            suffix=".rsp", prefix="logger-test-reponse-", text=True
        )
        os.write(fd, bytes("-I p0 -isystem p1", "utf-8"))
        os.close(fd)
        try:
            self.assume_successful_command(
                [clang, f"@{rsp_file}", file, "-Werror", "-o", binary],
                logger_env,
            )
            self.assume_successful_command(
                [binary], env=empty_env, outs="--VARIABLE--"
            )
            self.assert_json(
                command=f"{clang} @{rsp_file} {file} -Werror -o {binary}",
                file=file,
            )
        finally:
            os.remove(rsp_file)

    def test_response_file_contain_source_file(self):
        """
        Test if the clang-specific response file spells the
        source file under compilation instead of the command-line.
        """
        logger_env = self.get_envvars()
        # clang might need Z3
        logger_env = append_host_LD_LIBRARY_PATH(logger_env)
        file = self.source_file
        binary = self.binary_file
        clang = shutil.which("clang")
        if not clang:
            self.skipTest(
                f"No compiler matches the 'clang' pattern in your PATH"
            )

        fd, rsp_file = tempfile.mkstemp(
            suffix=".rsp", prefix="logger-test-reponse-", text=True
        )
        os.write(fd, bytes(f"-I p0 -isystem p1 {file}", "utf-8"))
        os.close(fd)
        try:
            self.assume_successful_command(
                [clang, f"@{rsp_file}", "-Werror", "-o", binary], logger_env
            )
            self.assume_successful_command(
                [binary], env=empty_env, outs="--VARIABLE--"
            )
            self.assert_json(
                command=f"{clang} @{rsp_file} -Werror -o {binary}",
                file=f"@{rsp_file}",
            )
        finally:
            os.remove(rsp_file)

    def test_compiler_abs(self):
        """
        Test if using an absolute path for the
        invocation, an absolute PATH will be logged.
        BTW we log absolute paths in every case anyway.
        """
        logger_env = self.get_envvars()
        file = self.source_file
        binary = self.binary_file
        gcc_abs = shutil.which("gcc")
        self.assume_successful_command(
            [gcc_abs, file, "-Werror", "-o", binary], logger_env
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--VARIABLE--"
        )
        self.assert_json(
            command=f"{gcc_abs} {file} -Werror -o {binary}",
            file=file,
        )

    def test_include_abs1(self):
        """Test if relative paths get logged as absolute ones."""
        logger_env = self.get_envvars()
        logger_env["CC_LOGGER_ABS_PATH"] = "1"
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            ["gcc", "-Ihello", file, "-Werror", "-o", binary], logger_env
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--VARIABLE--"
        )
        self.assert_json(
            command=f"gcc -I{REPO_ROOT}/hello {file} -Werror "
                    f"-o {binary}",
            file=file,
        )

    def test_include_abs2(self):
        """Same as test_include_abs1() but separating the '-I' and the path."""
        logger_env = self.get_envvars()
        logger_env["CC_LOGGER_ABS_PATH"] = "1"
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            ["gcc", "-I", "hello", file, "-Werror", "-o", binary], logger_env
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--VARIABLE--"
        )
        self.assert_json(
            command=f"gcc -I {REPO_ROOT}/hello {file} -Werror "
                    f"-o {binary}",
            file=file,
        )

    def test_include_abs3(self):
        """Same as test_include_abs1() but using equal sign (=)."""
        logger_env = self.get_envvars()
        logger_env["CC_LOGGER_ABS_PATH"] = "1"
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            ["gcc", "-isystem=hello", file, "-Werror", "-o", binary],
            logger_env,
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--VARIABLE--"
        )
        self.assert_json(
            command=f"gcc -isystem={REPO_ROOT}/hello {file} -Werror "
                    f"-o {binary}",
            file=file,
        )

    def test_source_abs(self):
        """
        Test if compiling from a specific directory the directory will be
        set accordingly in the log file.
        """
        logger_env = self.get_envvars()
        file = self.source_file
        binary = self.binary_file
        binary_dirname = os.path.dirname(binary)
        binary_basename = os.path.basename(binary)
        self.assume_successful_command(
            ["gcc", file, "-Werror", "-o", binary_basename],
            logger_env,
            cwd=binary_dirname,
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--VARIABLE--"
        )
        self.assert_json(
            command=f"gcc {file} -Werror -o {binary_basename}",
            file=file,
            directory=binary_dirname,
        )
