# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Test the build commands escaping and execution."""

import json
import os
import shutil
import tempfile
import unittest
from contextlib import closing

try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO

from libcodechecker.log import build_manager
from libcodechecker.analyze import log_parser
from libcodechecker.analyze.analyzers import analyzer_base
from libcodechecker.libhandlers.analyze import ParseLogOptions


class BuildCmdTestNose(unittest.TestCase):
    """
    Test the build command escaping and execution.
    """

    @classmethod
    def setup_class(cls):
        """
        Make a temporary directory and generate a source file
        which will be built.
        """
        cls.tmp_dir = tempfile.mkdtemp()
        cls.src_file_name = "main.cpp"
        cls.src_file_path = os.path.join(cls.tmp_dir,
                                         cls.src_file_name)
        cls.compiler = "clang++"

        with open(cls.src_file_path, "w") as test_src:
            test_src.write("""
            #include <iostream>

            #ifndef MYPATH
            #define MYPATH "/some/path"
            #endif

            int main(){
            std::cout<< MYPATH << std::endl;
            return 0;
            }""")

    @classmethod
    def teardown_class(cls):
        """
        Clean temporary directory and files.
        """
        dir_to_clean = cls.tmp_dir
        shutil.rmtree(dir_to_clean)

    def __get_cmp_json(self, buildcmd):
        """
        Generate a compile command json file.
        """

        compile_cmd = {"directory": self.tmp_dir,
                       "command": buildcmd + " -c " + self.src_file_path,
                       "file": self.src_file_path}

        compile_cmds = [compile_cmd]
        return json.dumps(compile_cmds)

    def __get_comp_actions(self, compile_cmd):
        """
        Generate a compilation command json file and parse it
        to return the compilation actions.
        """
        comp_cmd_json = self.__get_cmp_json(compile_cmd)
        with closing(StringIO()) as text:
            text.write(comp_cmd_json)

            return log_parser.parse_compile_commands_json(text,
                                                          ParseLogOptions())

    def test_buildmgr(self):
        """
        Check some simple command to be executed by
        the build manager.
        """
        cmd = 'cd ' + self.tmp_dir + ' && echo "test"'
        print("Running: " + cmd)
        ret_val = build_manager.execute_buildcmd(cmd)
        self.assertEqual(ret_val, 0)

    def test_analyzer_exec_double_quote(self):
        """
        Test the process execution by the analyzer,
        If the escaping fails the source file will not compile.
        """
        compile_cmd = self.compiler + \
            ' -DDEBUG \'-DMYPATH="/this/some/path/"\''

        comp_actions = self.__get_comp_actions(compile_cmd)

        for comp_action in comp_actions:
            for source in comp_action.sources:
                cmd = [self.compiler]
                cmd.extend(comp_action.analyzer_options)
                cmd.append(str(source))
                cwd = comp_action.directory

                print(cmd)
                print(cwd)

                ret_val, stdout, stderr = analyzer_base.SourceAnalyzer \
                    .run_proc(' '.join(cmd), cwd=cwd)

                print(stdout)
                print(stderr)
                self.assertEqual(ret_val, 0)

    def test_analyzer_ansic_double_quote(self):
        """
        Test the process execution by the analyzer with ansi-C like
        escape characters in it \".
        If the escaping fails the source file will not compile.
        """
        compile_cmd = self.compiler + ''' '-DMYPATH=\"/some/other/path\"' '''
        comp_actions = self.__get_comp_actions(compile_cmd)

        for comp_action in comp_actions:
            for source in comp_action.sources:
                cmd = [self.compiler]
                cmd.extend(comp_action.analyzer_options)
                cmd.append(str(source))
                cwd = comp_action.directory

                print(cmd)
                print(cwd)

                ret_val, stdout, stderr = analyzer_base.SourceAnalyzer \
                    .run_proc(' '.join(cmd), cwd=cwd)

                print(stdout)
                print(stderr)

                self.assertEqual(ret_val, 0)
