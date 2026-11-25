import base64
import io
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from codechecker_api.python.DBAccess_v6 import ttypes

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
            output_format="json",
            details=True
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


class ConvertReportDataToReportTest(unittest.TestCase):
    """
    Regression tests for https://github.com/Ericsson/codechecker/issues/3909
    """

    def setUp(self):
        cmd_line_client.LOG = SimpleNamespace(
            error=Mock(), warning=Mock(), info=Mock(), debug=Mock())

        self.tmp_dir = tempfile.TemporaryDirectory()
        self.source = os.path.join(self.tmp_dir.name, "main.c")
        with open(self.source, "w", encoding="utf-8") as f:
            f.write("int main() { return 0; }\n")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def report_data(self):
        return ttypes.ReportData(
            fileId=1,
            checkedFile=self.source,
            line=1,
            column=1,
            checkerMsg="message",
            checkerId="checker",
            severity=ttypes.Severity.HIGH,
            bugHash="hash",
            analyzerName="clangsa")

    def test_source_content_from_server(self):
        """ The file content sent by the server is used. """
        client = Mock()
        client.getSourceFileData.return_value = ttypes.SourceFileData(
            fileId=1,
            filePath=self.source,
            fileContent=base64.b64encode(b"server content").decode())

        reports = cmd_line_client.convert_report_data_to_report(
            client, [self.report_data()], ["html"])

        self.assertEqual(reports[0].file.content, "server content")
        cmd_line_client.LOG.warning.assert_not_called()

    def test_missing_source_content_on_server(self):
        """
        If the server has no content for the file (e.g. the file was removed
        from the database), a warning is logged instead of crashing and the
        local version of the file is used.
        """
        client = Mock()
        client.getSourceFileData.return_value = ttypes.SourceFileData()

        reports = cmd_line_client.convert_report_data_to_report(
            client, [self.report_data()], ["html"])

        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].file.content,
                         "int main() { return 0; }\n")
        cmd_line_client.LOG.warning.assert_called_once()
        self.assertIn(self.source,
                      cmd_line_client.LOG.warning.call_args[0])

    def test_report_without_source_file_on_server(self):
        """
        A report whose source file is not in the server's database anymore
        is skipped with a warning, the other reports are kept.
        """
        missing = ttypes.ReportData(
            fileId=2,
            checkedFile=None,
            line=3,
            column=1,
            checkerMsg="missing",
            checkerId="missing.checker",
            severity=ttypes.Severity.HIGH,
            bugHash="missing_hash",
            analyzerName="clangsa")

        for output_format in ["html", "table"]:
            with self.subTest(output_format=output_format):
                cmd_line_client.LOG.warning.reset_mock()
                client = Mock()
                client.getSourceFileData.return_value = \
                    ttypes.SourceFileData(
                        fileId=1,
                        filePath=self.source,
                        fileContent=base64.b64encode(b"content").decode())
                client.getLinesInSourceFileContents.return_value = {
                    1: {1: base64.b64encode(b"content").decode()}}

                reports = cmd_line_client.convert_report_data_to_report(
                    client, [missing, self.report_data()], [output_format])

                self.assertEqual([r.checker_name for r in reports],
                                 ["checker"])
                cmd_line_client.LOG.warning.assert_called_once()
                self.assertIn("missing.checker",
                              cmd_line_client.LOG.warning.call_args[0])

                # Nothing is requested from the server about the missing file.
                for call in client.getSourceFileData.call_args_list:
                    self.assertNotEqual(call[0][0], 2)
                for call in client.getLinesInSourceFileContents.call_args_list:
                    self.assertNotIn(2, [r.fileId for r in call[0][0]])
