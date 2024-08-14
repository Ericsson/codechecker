#!/usr/bin/env python3
# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import json
import os
import platform
import shlex
import subprocess
import tempfile
import unittest
from typing import Mapping, Optional, Tuple, Sequence

REPO_ROOT = os.path.abspath(os.getenv("REPO_ROOT"))
LOGGER_DIR = os.path.join(REPO_ROOT, "build")


def run_command(
    cmd: Sequence[str],
    cwd: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Tuple[int, str, str]:
    cmd = " ".join([shlex.quote(c) for c in cmd])
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            shell=True,
            encoding="utf-8",
            universal_newlines=True,
            errors="ignore",
        )
        stdout, stderr = proc.communicate()
        retcode = proc.returncode
    except FileNotFoundError:
        return 2, "", ""
    return retcode, stdout, stderr


_PRINT_STRINGIFIED_VARIABLE_CODE = """
#include <stdio.h>
#define xstr(a) str(a)
#define str(a) #a
int main() {
  char buf[] = xstr(VARIABLE); // It might containt null characters.
  printf("--");
  for (unsigned i = 0; sizeof(buf) > 1 && i < sizeof(buf) - 1; ++i)
    printf("%c", buf[i]);
  printf("--");
}
"""
"""
The 'VARIABLE' define will be passed as a command line parameter to the
test file. This way we can run the result and validate the runtime behavior.
"""

empty_env = {"PATH": "/usr/bin"}


class BasicLoggerTest(unittest.TestCase):
    def setUp(self):
        fd, self.source_file = tempfile.mkstemp(
            suffix=".cpp", prefix="logger-test-source-", text=True
        )
        os.write(fd, bytes(_PRINT_STRINGIFIED_VARIABLE_CODE, "utf-8"))
        os.close(fd)
        fd, self.logger_file = tempfile.mkstemp(
            suffix=".json", prefix="logger-test-db-", text=True
        )
        os.close(fd)
        fd, self.binary_file = tempfile.mkstemp(
            suffix=".out", prefix="logger-test-binary-"
        )
        os.close(fd)
        fd, self.logger_debug_file = tempfile.mkstemp(
            suffix=".log", prefix="logger-test-debug-", text=True
        )
        os.close(fd)

    def tearDown(self):
        tmp_files = [
            self.source_file,
            self.logger_file,
            self.binary_file,
            self.logger_debug_file,
            self.logger_debug_file + ".lock",
        ]
        for file in tmp_files:
            try:
                os.remove(file)
            except FileNotFoundError:
                pass

    def read_actual_json(self) -> str:
        with open(self.logger_file, "r") as fd:
            return fd.read()

    def get_envvars(self) -> Mapping[str, str]:
        return {
            "PATH": os.getenv("PATH"),
            "LD_PRELOAD": "ldlogger.so",
            "LD_LIBRARY_PATH": os.path.join(LOGGER_DIR, "lib"),
            "CC_LOGGER_GCC_LIKE": "gcc:g++:clang:clang++:cc:c++",
            "CC_LOGGER_FILE": self.logger_file,
            "CC_LOGGER_DEBUG_FILE": self.logger_debug_file,
        }

    def assume_successful_command(
        self,
        cmd: Sequence[str],
        env: Mapping[str, str],
        cwd: str = REPO_ROOT,
        outs: str = "",
        errs: str = "",
    ):
        retcode, stdout, stderr = run_command(cmd=cmd, env=env, cwd=cwd)
        self.assertEqual(stdout, outs)
        self.assertEqual(stderr, errs)
        self.assertEqual(retcode, 0)

    def assert_json(
        self,
        command: str,
        file: str,
        directory: str = REPO_ROOT,
    ):
        parsed_json = json.loads(self.read_actual_json())

        # Validate the structure of the json object.
        self.assertTrue(isinstance(parsed_json, list))
        self.assertEqual(len(parsed_json), 1)
        entry = parsed_json[0]

        self.assertTrue(entry["command"])
        self.assertTrue(entry["file"])
        self.assertTrue(entry["directory"])
        self.assertTrue(os.path.isdir(entry["directory"]))

        # Validate the json content.
        self.assertEqual(entry["file"], file)
        self.assertEqual(entry["directory"], directory)

        # Check only the suffix of the command.
        # The place where gcc resides might differ on some platforms.
        self.assertTrue(entry["command"].endswith(command))
