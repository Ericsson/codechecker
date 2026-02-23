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
    def test_enabled_checkers_json(self, get_run_data, setup_client, init_logger):
        client = Mock()
        setup_client.return_value = client
        get_run_data.return_value = [DummyRun(1)]

        client.getAnalysisInfo.return_value = [
            make_analysis_info({"clangsa": {"a": True}})
        ]
        client.getAnalysisStatistics.return_value = {
            "clangsa": SimpleNamespace(
                version="1",
                failed=0,
                successful=1,
                failedFilePaths=[],
            )
        }

        args = Args(
            product_url="dummy",
            sort_type="name",
            sort_order="asc",
            output_format="json"
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_line_client.handle_list_runs(args)

        data = json.loads(buf.getvalue())
        self.assertEqual(len(data), 1)
        run_entry = data[0]
        self.assertEqual(len(run_entry), 1)
        _, run_data = next(iter(run_entry.items()))
        self.assertIn("analyzerStatistics", run_data)
        self.assertIn("clangsa", run_data["analyzerStatistics"])
        stats = run_data["analyzerStatistics"]["clangsa"]
        self.assertIn("enabledCheckers", stats)
        self.assertEqual(stats["enabledCheckers"], ["a"])
