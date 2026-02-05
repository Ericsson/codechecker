import io
import json
import unittest
from types import SimpleNamespace
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from codechecker_client import cmd_line_client


class Args(SimpleNamespace):
    def __contains__(self, key):
        return hasattr(self, key)


class DummyRun:
    def __init__(self, runId, name="r"):
        self.runId = runId
        self.name = name
        self.resultCount = 0
        self.analyzerStatistics = {}
        self.runDate = ""
        self.versionTag = ""
        self.duration = 0
        self.description = ""
        self.codeCheckerVersion = ""


class DummyCheckerCfg:
    def __init__(self, enabled):
        self.enabled = enabled


def make_analysis_info(checkers_dict):
    checkers = {}
    for analyzer, ckrs in checkers_dict.items():
        checkers[analyzer] = {name: DummyCheckerCfg(en) for name, en in ckrs.items()}
    return SimpleNamespace(checkers=checkers)


class ListRunsEnabledCheckersTest(unittest.TestCase):
    def setUp(self):
        cmd_line_client.LOG = SimpleNamespace(error=Mock(), warning=Mock(), info=Mock())

    @patch("codechecker_client.cmd_line_client.init_logger")
    @patch("codechecker_client.cmd_line_client.setup_client")
    @patch("codechecker_client.cmd_line_client.get_run_data")
    def test_enabled_checkers_plaintext(self, get_run_data, setup_client, init_logger):
        client = Mock()
        setup_client.return_value = client

        runs = [DummyRun(1)]
        get_run_data.return_value = runs

        client.getAnalysisInfo.return_value = [
            make_analysis_info({
                "clangsa": {"core.CallAndMessage": True, "unix.Malloc": False},
                "clang-tidy": {"modernize-use-nullptr": True},
            })
        ]

        args = Args(
            product_url="dummy",
            sort_type="name",
            sort_order="asc",
            output_format="plaintext",
            enabled_checkers=True
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_line_client.handle_list_runs(args)

        out = buf.getvalue()
        self.assertIn("clangsa:\n", out)
        self.assertIn("  core.CallAndMessage\n", out)
        self.assertNotIn("unix.Malloc", out)
        self.assertIn("clang-tidy:\n", out)
        self.assertIn("  modernize-use-nullptr\n", out)

    @patch("codechecker_client.cmd_line_client.init_logger")
    @patch("codechecker_client.cmd_line_client.setup_client")
    @patch("codechecker_client.cmd_line_client.get_run_data")
    def test_enabled_checkers_csv(self, get_run_data, setup_client, init_logger):
        client = Mock()
        setup_client.return_value = client
        get_run_data.return_value = [DummyRun(1)]

        client.getAnalysisInfo.return_value = [
            make_analysis_info({"clangsa": {"a": True, "b": False}})
        ]

        args = Args(
            product_url="dummy",
            sort_type="name",
            sort_order="asc",
            output_format="csv",
            enabled_checkers=True
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_line_client.handle_list_runs(args)

        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        self.assertEqual(lines[0], "Analyzer;Checker")
        self.assertIn("clangsa;a", lines)
        self.assertTrue(all("clangsa;b" not in l for l in lines))

    @patch("codechecker_client.cmd_line_client.init_logger")
    @patch("codechecker_client.cmd_line_client.setup_client")
    @patch("codechecker_client.cmd_line_client.get_run_data")
    def test_enabled_checkers_json(self, get_run_data, setup_client, init_logger):
        client = Mock()
        setup_client.return_value = client
        get_run_data.return_value = [DummyRun(1)]

        client.getAnalysisInfo.return_value = [
            make_analysis_info({"clangsa": {"a": True}})
        ]

        args = Args(
            product_url="dummy",
            sort_type="name",
            sort_order="asc",
            output_format="json",
            enabled_checkers=True
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_line_client.handle_list_runs(args)

        data = json.loads(buf.getvalue())
        self.assertEqual(data, {"clangsa": ["a"]})

    @patch("codechecker_client.cmd_line_client.init_logger")
    @patch("codechecker_client.cmd_line_client.setup_client")
    @patch("codechecker_client.cmd_line_client.get_run_data")
    def test_enabled_checkers_table(self, get_run_data, setup_client, init_logger):
        client = Mock()
        setup_client.return_value = client
        get_run_data.return_value = [DummyRun(1)]

        client.getAnalysisInfo.return_value = [
            make_analysis_info({"clangsa": {"a": True}})
        ]

        with patch("codechecker_client.cmd_line_client.twodim.to_str", return_value="TABLE_OUT") as to_str:
            args = Args(
                product_url="dummy",
                sort_type="name",
                sort_order="asc",
                output_format="table",
                enabled_checkers=True
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_line_client.handle_list_runs(args)

            to_str.assert_called_once()
            out = buf.getvalue().strip()
            self.assertEqual(out, "TABLE_OUT")

    @patch("codechecker_client.cmd_line_client.init_logger")
    @patch("codechecker_client.cmd_line_client.setup_client")
    @patch("codechecker_client.cmd_line_client.get_run_data")
    def test_enabled_checkers_unsupported_format_logs_error(self, get_run_data, setup_client, init_logger):
        client = Mock()
        setup_client.return_value = client
        get_run_data.return_value = [DummyRun(1)]

        client.getAnalysisInfo.return_value = [
            make_analysis_info({"clangsa": {"a": True}})
        ]

        args = Args(
            product_url="dummy",
            sort_type="name",
            sort_order="asc",
            output_format="xml",
            enabled_checkers=True
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_line_client.handle_list_runs(args)

        self.assertEqual(buf.getvalue(), "")
        cmd_line_client.LOG.error.assert_called_once()
