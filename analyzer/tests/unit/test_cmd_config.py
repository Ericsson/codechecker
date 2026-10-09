# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Tests for the command line options read from a configuration file.
"""


import json
import os
import tempfile
import unittest
from argparse import Namespace

from codechecker_common import cmd_config


class CmdConfigTest(unittest.TestCase):
    """ Test the parsing of configuration file options. """

    def setUp(self):
        self.workspace = tempfile.mkdtemp()
        self.json_file = os.path.join(self.workspace, "codechecker.json")
        self.yaml_file = os.path.join(self.workspace, "codechecker.yaml")
        self.yml_file = os.path.join(self.workspace, "codechecker.yml")

    def _write_json(self, content):
        with open(self.json_file, 'w', encoding="utf-8") as config_file:
            json.dump(content, config_file)
        return self.json_file

    def _write_yaml(self, content, path=None):
        path = path or self.yaml_file
        with open(path, 'w', encoding="utf-8") as config_file:
            config_file.write(content)
        return path

    def _process(self, config_path, subcommand="analyze"):
        # argparse.Namespace supports both 'in' and attribute access, which is
        # what process_config_file expects of a real parsed argument list.
        args = Namespace(config_file=config_path)
        return cmd_config.process_config_file(args, subcommand)

    # ------------------------------------------------------------------
    # YAML: several arguments in one entry.
    # ------------------------------------------------------------------

    def test_yaml_multiple_arguments_in_one_entry(self):
        """
        A whitespace separated entry must produce one argument per token.
        """
        config_file = self._write_yaml("""
analyze:
  - --analyzers clangsa clang-tidy
  - --enable=core.DivideZero
""")
        self.assertEqual(
            self._process(config_file),
            ["--analyzers", "clangsa", "clang-tidy",
             "--enable=core.DivideZero"])

    def test_yaml_separate_entries_still_work(self):
        """
        The pre-existing one-argument-per-entry syntax is unchanged.
        """
        config_file = self._write_yaml("""
analyze:
  - --analyzers
  - clangsa
  - --enable=core.DivideZero
""")
        self.assertEqual(
            self._process(config_file),
            ["--analyzers", "clangsa", "--enable=core.DivideZero"])

    def test_yaml_single_argument_entry_is_unchanged(self):
        config_file = self._write_yaml("""
analyze:
  - --clean
""")
        self.assertEqual(self._process(config_file), ["--clean"])

    # ------------------------------------------------------------------
    # YAML: quoting.
    # ------------------------------------------------------------------

    def test_yaml_quoted_value_with_space(self):
        """
        A value containing a space must survive tokenization as one argument.
        """
        config_file = self._write_yaml("""
analyze:
  - --trim-path-prefix "/tmp/my project"
""")
        self.assertEqual(
            self._process(config_file),
            ["--trim-path-prefix", "/tmp/my project"])

    def test_yaml_quoted_value_with_space_single_quotes(self):
        config_file = self._write_yaml("""
parse:
  - '--trim-path-prefix "/tmp/my project"'
""")
        self.assertEqual(
            self._process(config_file, subcommand="parse"),
            ["--trim-path-prefix", "/tmp/my project"])

    def test_yaml_escaped_space_in_value(self):
        config_file = self._write_yaml("""
analyze:
  - --define=FOO=bar\\ baz
""")
        self.assertEqual(self._process(config_file), ["--define=FOO=bar baz"])

    def test_yaml_empty_entry_is_skipped(self):
        config_file = self._write_yaml("""
analyze:
  - --clean
  - ""
  - --verbose=debug
""")
        self.assertEqual(
            self._process(config_file),
            ["--clean", "--verbose=debug"])

    def test_yaml_hash_is_not_a_comment(self):
        """
        A '#' inside an entry is data. YAML stripping a trailing '#' in an
        unquoted scalar is YAML's business; shlex must not strip it again.
        """
        config_file = self._write_yaml("""
analyze:
  - '--flag=value#hash'
""")
        self.assertEqual(self._process(config_file), ["--flag=value#hash"])

    # ------------------------------------------------------------------
    # YAML: invalid quoting.
    # ------------------------------------------------------------------

    def test_yaml_invalid_quoting_raises_with_context(self):
        """
        An unterminated quote must produce an error naming the file and the
        section, not a bare ValueError.
        """
        config_file = self._write_yaml("""
analyze:
  - --trim-path-prefix "/tmp/my project
""")
        with self.assertRaises(cmd_config.ConfigFileTokenizeError) as caught:
            self._process(config_file)
        message = str(caught.exception)
        self.assertIn(config_file, message)
        self.assertIn("analyze", message)

    # ------------------------------------------------------------------
    # YAML: extensions and subcommands.
    # ------------------------------------------------------------------

    def test_yml_extension_is_treated_as_yaml(self):
        config_file = self._write_yaml("""
analyze:
  - --analyzers clangsa clang-tidy
""", path=self.yml_file)
        self.assertEqual(
            self._process(config_file),
            ["--analyzers", "clangsa", "clang-tidy"])

    def test_yaml_analyzer_alias(self):
        """ The 'analyzer' section is the backward compatible alias. """
        config_file = self._write_yaml("""
analyzer:
  - --analyzers clangsa clang-tidy
""")
        self.assertEqual(
            self._process(config_file),
            ["--analyzers", "clangsa", "clang-tidy"])

    def test_yaml_analyze_takes_precedence_over_analyzer(self):
        config_file = self._write_yaml("""
analyze:
  - --analyzers clangsa
analyzer:
  - --analyzers clang-tidy
""")
        self.assertEqual(self._process(config_file),
                         ["--analyzers", "clangsa"])

    def test_yaml_check_merges_analyze_and_parse(self):
        """
        'check' combines both sections, and both are tokenized.
        """
        config_file = self._write_yaml("""
analyze:
  - --analyzers clangsa clang-tidy
parse:
  - --trim-path-prefix "/tmp/my project"
""")
        self.assertEqual(
            self._process(config_file, subcommand="check"),
            ["--analyzers", "clangsa", "clang-tidy",
             "--trim-path-prefix", "/tmp/my project"])

    def test_yaml_other_subcommand_section(self):
        config_file = self._write_yaml("""
server:
  - --port 9090
""")
        self.assertEqual(
            self._process(config_file, subcommand="server"),
            ["--port", "9090"])

    def test_yaml_missing_section_returns_empty(self):
        config_file = self._write_yaml("""
analyze:
  - --clean
""")
        self.assertEqual(self._process(config_file, subcommand="store"), [])

    # ------------------------------------------------------------------
    # JSON: behavior must not change.
    # ------------------------------------------------------------------

    def test_json_is_not_tokenized(self):
        """
        JSON has always been one-entry-per-argument, including entries that
        contain a space.
        """
        config_file = self._write_json({
            "analyze": ["--analyzers clangsa clang-tidy",
                        "--enable=core.DivideZero"]})
        self.assertEqual(
            self._process(config_file),
            ["--analyzers clangsa clang-tidy", "--enable=core.DivideZero"])

    def test_json_unchanged_for_ordinary_options(self):
        config_file = self._write_json({
            "analyze": ["--analyzers", "clangsa"],
            "parse": ["--trim-path-prefix", "/workspace"]})
        self.assertEqual(
            self._process(config_file),
            ["--analyzers", "clangsa"])
        self.assertEqual(
            self._process(config_file, subcommand="parse"),
            ["--trim-path-prefix", "/workspace"])

    def test_json_check_merges_sections(self):
        config_file = self._write_json({
            "analyzer": ["--analyzers", "clangsa"],
            "parse": ["--trim-path-prefix", "/workspace"]})
        self.assertEqual(
            self._process(config_file, subcommand="check"),
            ["--analyzers", "clangsa", "--trim-path-prefix", "/workspace"])

    # ------------------------------------------------------------------
    # Tokenizer unit itself.
    # ------------------------------------------------------------------

    def test_tokenize_entry_preserves_equals_form(self):
        self.assertEqual(
            cmd_config._tokenize_entry(
                "--analyzer-config=clangsa:unroll-loops=true",
                "cfg.yaml", "analyze"),
            ["--analyzer-config=clangsa:unroll-loops=true"])

    # ------------------------------------------------------------------
    # Windows paths (added 2026-09-12 after review feedback).
    # ------------------------------------------------------------------

    def test_windows_path_backslashes_are_preserved(self):
        """
        A backslash in a Windows path is a separator, not an escape. POSIX
        tokenization would otherwise turn 'C:\\Users\\me' into 'C:Usersme'.
        """
        config_file = self._write_yaml(
            "analyze:\n"
            "  - --trim-path-prefix=C:\\Users\\me\\workspace\n")
        self.assertEqual(
            self._process(config_file),
            ["--trim-path-prefix=C:\\Users\\me\\workspace"])

    def test_windows_path_without_spaces_is_unchanged(self):
        """
        An entry with no spaces must keep working, including on Windows.
        """
        config_file = self._write_yaml(
            "analyze:\n"
            "  - --skip=C:\\project\\skip.txt\n")
        self.assertEqual(
            self._process(config_file),
            ["--skip=C:\\project\\skip.txt"])

    def test_escaped_space_still_collapses(self):
        """
        A backslash before a space is still an escape, so the two meanings do
        not conflict.
        """
        config_file = self._write_yaml(
            "analyze:\n"
            "  - --define=FOO=bar\\ baz\n")
        self.assertEqual(
            self._process(config_file),
            ["--define=FOO=bar baz"])

    # ------------------------------------------------------------------
    # Section labels in diagnostics (added 2026-09-12).
    # ------------------------------------------------------------------

    def test_analyzer_alias_is_named_in_diagnostics(self):
        """
        Diagnostics must name the section the user actually wrote, even when
        the backward compatible 'analyzer' key is used.
        """
        config_file = self._write_yaml("""
analyzer:
  - --analyzers clangsa clang-tidy
""")
        with self.assertLogs('system', level='INFO') as captured:
            cmd_config.process_config_file(
                Namespace(config_file=config_file), 'analyze')
        self.assertTrue(any("under 'analyzer'" in line
                            for line in captured.output))

    def test_analyze_key_is_named_in_diagnostics(self):
        config_file = self._write_yaml("""
analyze:
  - --analyzers clangsa clang-tidy
""")
        with self.assertLogs('system', level='INFO') as captured:
            cmd_config.process_config_file(
                Namespace(config_file=config_file), 'analyze')
        self.assertTrue(any("under 'analyze'" in line
                            for line in captured.output))

    def test_tokenize_entry_rejects_non_string(self):
        with self.assertRaises(cmd_config.ConfigFileTokenizeError):
            cmd_config._tokenize_entry(42, "cfg.yaml", "analyze")
