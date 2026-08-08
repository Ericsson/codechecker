# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Tests for the report-converter CLI, specifically the '--example' flag and
the EXAMPLE_CMD interface it relies on (see
https://github.com/Ericsson/codechecker/issues/4992).
"""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from codechecker_report_converter import cli


# TOOL_NAMEs of analyzers that do not yet provide an EXAMPLE_CMD.
#
# This list must not grow: any newly added parser is required to define a
# non-empty EXAMPLE_CMD (see AnalyzerResultBase.EXAMPLE_CMD). Existing
# parsers on this list predate that requirement and should have one added
# as a follow-up; when a parser is updated, remove it from this list.
LEGACY_ANALYZERS_WITHOUT_EXAMPLE_CMD = {
    'clang-tidy', 'clang-tidy-yaml', 'coccinelle', 'cppcheck', 'cpplint',
    'eslint', 'gcc', 'golint', 'fbinfer', 'jscpd', 'kernel-doc', 'mdl',
    'pmd', 'pvs-studio', 'pyflakes', 'pylint', 'roslynator', 'smatch',
    'sparse', 'sphinx', 'spotbugs', 'tslint',
    'asan', 'lsan', 'msan', 'tsan', 'ubsan',
}


class ExampleCmdInterfaceTest(unittest.TestCase):
    """
    Ensures new analyzer parsers can't be added without a usage example,
    while allowing existing ones to be migrated gradually.
    """

    def test_new_analyzers_must_define_example_cmd(self):
        for tool_name, analyzer_result in cli.supported_converters.items():
            if tool_name in LEGACY_ANALYZERS_WITHOUT_EXAMPLE_CMD:
                continue

            self.assertTrue(
                analyzer_result.EXAMPLE_CMD,
                f"'{tool_name}' must define a non-empty EXAMPLE_CMD class "
                "attribute (see AnalyzerResultBase.EXAMPLE_CMD) so users "
                "can discover how to produce compatible input via "
                "'report-converter --example {tool_name}'.")

    def test_legacy_exemption_list_has_no_stale_entries(self):
        """
        Keeps the exemption list itself honest: every entry must still
        correspond to a supported analyzer that genuinely lacks an
        EXAMPLE_CMD. Once a legacy parser is updated, it must be removed
        from this list rather than left behind.
        """
        for tool_name in LEGACY_ANALYZERS_WITHOUT_EXAMPLE_CMD:
            self.assertIn(tool_name, cli.supported_converters)
            self.assertFalse(
                cli.supported_converters[tool_name].EXAMPLE_CMD,
                f"'{tool_name}' now defines an EXAMPLE_CMD - please remove "
                "it from LEGACY_ANALYZERS_WITHOUT_EXAMPLE_CMD.")


class ExampleFlagTest(unittest.TestCase):
    """ Tests for the 'report-converter --example TYPE' flag. """

    def test_example_flag_prints_example_and_exits_zero(self):
        """
        For an analyzer with an EXAMPLE_CMD, '--example' should print it
        and exit successfully, without requiring the tool's other
        required arguments (input, --output, --type).
        """
        out = io.StringIO()
        with patch('sys.argv', ['report-converter', '--example', 'ruff']), \
                redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                cli.main()

        self.assertEqual(ctx.exception.code, 0)
        self.assertIn('ruff check', out.getvalue())
        self.assertIn('report-converter -t ruff', out.getvalue())

    def test_example_flag_on_legacy_analyzer_does_not_crash(self):
        """
        For an analyzer that doesn't have an EXAMPLE_CMD yet, '--example'
        should exit cleanly (with a warning) instead of crashing.
        """
        with patch('sys.argv', ['report-converter', '--example', 'pylint']):
            with self.assertRaises(SystemExit) as ctx:
                cli.main()

        self.assertEqual(ctx.exception.code, 0)

    def test_example_flag_rejects_unknown_analyzer(self):
        """
        An unsupported TYPE should be rejected the same way argparse
        rejects any other invalid 'choices' value.
        """
        argv = ['report-converter', '--example', 'not_a_real_analyzer']
        with patch('sys.argv', argv):
            with self.assertRaises(SystemExit) as ctx:
                cli.main()

        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
