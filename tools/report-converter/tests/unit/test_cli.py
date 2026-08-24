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


class ExampleCmdInterfaceTest(unittest.TestCase):
    """
    Ensures every supported analyzer parser defines a usage example, and
    that no future parser can be added without one.
    """

    def test_all_analyzers_define_example_cmd(self):
        for tool_name, analyzer_result in cli.supported_converters.items():
            self.assertTrue(
                analyzer_result.EXAMPLE_CMD,
                f"'{tool_name}' must define a non-empty EXAMPLE_CMD class "
                "attribute (see AnalyzerResultBase.EXAMPLE_CMD) so users "
                "can discover how to produce compatible input via "
                f"'report-converter --example {tool_name}'.")


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

    def test_example_flag_on_analyzer_without_example_does_not_crash(self):
        """
        Every real analyzer currently defines an EXAMPLE_CMD, but the
        fallback path for one that doesn't (e.g. a newly added parser
        mid-development) must still exit cleanly with a warning instead
        of crashing.
        """
        tool_name = next(iter(cli.supported_converters))
        analyzer_result = cli.supported_converters[tool_name]
        original_example_cmd = analyzer_result.EXAMPLE_CMD
        analyzer_result.EXAMPLE_CMD = ''
        try:
            argv = ['report-converter', '--example', tool_name]
            with patch('sys.argv', argv):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main()
        finally:
            analyzer_result.EXAMPLE_CMD = original_example_cmd

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
