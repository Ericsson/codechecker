# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import json
import logging
import os

from sarif import loader

from typing import Any, Dict, List, Optional, Tuple

from urllib.parse import urlparse

from codechecker_report_converter.report import BugPathEvent, \
    BugPathPosition, File, MacroExpansion, get_or_create_file, Range, Report
from codechecker_report_converter.report.hash import get_report_hash, HashType
from codechecker_report_converter.report.parser.base import AnalyzerInfo, \
    BaseParser, load_json, get_tool_info


EXTENSION = 'sarif'


LOG = logging.getLogger('report-converter')


# §3.37
class ThreadFlowInfo:
    def __init__(self):
        self.bug_path_events: List[BugPathEvent] = []
        self.bug_path_positions: List[BugPathPosition] = []
        self.notes: List[BugPathEvent] = []
        self.macro_expansions: List[MacroExpansion] = []


# Parse to/from sarif formats.
# Sarif has an extensive documentation, and supports a grand number of fields
# that CodeChecker has no use for as of writing this comment (e.g. §3.39 graph,
# §3.30 region), leading to these fields to be ignored.
# This is NOT (and will likely never be) a full fledged sarif parser, only what
# we need from it at the time.
class Parser(BaseParser):
    def get_reports(
        self,
        analyzer_result_file_path: str,
        _: Optional[str] = None
    ) -> List[Report]:
        """ Get reports from the given analyzer result file. """

        if not self.has_any_runs(analyzer_result_file_path):
            return []

        reports: List[Report] = []
        self.result_file_path = analyzer_result_file_path
        self.had_error = False

        data = loader.load_sarif_file(analyzer_result_file_path)

        for run in data.runs:
            rules = self._get_rules(run.run_data)
            analyzer_name = self._get_analyzer_name(run.run_data)
            # $3.14.14
            self.original_uri_base_ids = None
            if "originalUriBaseIds" in run.run_data:
                self.original_uri_base_ids = run.run_data["originalUriBaseIds"]

            if "results" not in run.run_data:
                continue

            for result in run.get_results():
                rule_id = result["ruleId"]
                message = self._process_message(
                    result["message"], rule_id, rules)  # §3.11

                thread_flow_info = self._process_code_flows(
                    result, rule_id, rules)
                for location in result.get("locations", []):
                    # TODO: We don't really support non-local analyses, so we
                    # only parse physical locations here.
                    file, rng = self._process_location(location)
                    if not (file and rng):
                        continue
                    if self.had_error:
                        return []

                    bug_path_events = thread_flow_info.bug_path_events or None

                    report = Report(
                        file, rng.start_line, rng.start_col,
                        message, rule_id,  # TODO: Add severity.
                        analyzer_name=analyzer_name,
                        analyzer_result_file_path=analyzer_result_file_path,
                        bug_path_events=bug_path_events,
                        bug_path_positions=thread_flow_info.bug_path_positions,
                        notes=thread_flow_info.notes,
                        macro_expansions=thread_flow_info.macro_expansions)

                    if report.report_hash is None:
                        report.report_hash = get_report_hash(
                            report, HashType.PATH_SENSITIVE)

                    reports.append(report)

        return reports

    def has_any_runs(self, result_file_path: str) -> bool:
        """
        The package that contains the sarif import, sarif-tools currently
        crashes when a sarif file contains no runs, so we need to manually
        check it.
        """
        ret = load_json(result_file_path)
        return bool(ret and ret["runs"])

    def _get_rules(self, data: Dict) -> Dict[str, Dict]:
        """
        The list of checkers as per §3.19.23. The standard doesn't
        explicitly state whether this is the list of available checkers, or
        enabled checkers, unfortunately.
        """
        rules: Dict[str, Dict] = {}

        driver = data["tool"]["driver"]
        for rule in driver.get("rules", []):
            rules[rule["id"]] = rule

        return rules

    def _get_analyzer_name(self, data: Dict) -> str:
        """ Get analyzer name from SARIF report. """
        return data.get("tool", {}).get("driver", {}).get("name", "unknown")

    def _process_code_flows(
        self,
        result: Dict,
        rule_id: str,
        rules: Dict[str, Dict]
    ) -> ThreadFlowInfo:
        """
        Parse threadFlows (§3.36.3), which is a list of threadFlow objects
        (§3.37), basically the components of a bug path (events, notes, arrows,
        etc).
        """

        thread_flow_info = ThreadFlowInfo()

        # TODO: Currently, we only collect bug path events.

        for code_flow in result.get("codeFlows", []):
            for thread_flow in code_flow.get("threadFlows", []):
                for location_data in thread_flow["locations"]:
                    # There are a lot data stored alongside the location worth
                    # parsing, but we only need the actual location now.
                    location = location_data["location"]

                    if "message" not in location:
                        # TODO: This might be a bug path position (for arrows).
                        continue

                    message = self._process_message(
                        location["message"], rule_id, rules)

                    file, rng = self._process_location(location)
                    if not (file and rng):
                        continue

                    thread_flow_info.bug_path_events.append(BugPathEvent(
                        message, file, rng.start_line, rng.start_col, rng))

        return thread_flow_info

    def _process_location(
        self,
        location: Dict,
    ) -> Tuple[Optional[File], Optional[Range]]:
        """
        Parse location (§3.28). Currently we only parse physical locations
        (§3.29), that describe a (file, range) pair, among other things.
        Sarif also supports logical locations (§3.33) that might describe
        a namespace, type, etc, but CodeChecker has no use for that.
        """
        physical_loc = location.get("physicalLocation")
        if physical_loc:
            file = self._get_file(physical_loc)
            rng = self._get_range(physical_loc)
            return file, rng

        return None, None

    def _get_range(self, physical_loc: Dict) -> Optional[Range]:
        """ Get range from a physical location. """
        region = physical_loc.get("region", {})
        start_line = region.get("startLine")
        if start_line is None:
            return None

        start_col = region.get("startColumn", 1)
        end_line = region.get("endLine", start_line)
        end_col = region.get("endColumn", start_col)

        return Range(start_line, start_col, end_line, end_col)

    def _resolve_uri_base_id(self, uri_base_id: str, postfix: str):
        """
        Try to assemble the leading part of the URI needed to find out the
        absolute path of the file. If this fails, we consider the entire sarif
        file invalid, not only this particular record.
        """
        error_str = \
            f"Failed to fully resolve the path for '{postfix}'. sarif " \
            "v2.1.0 permits this, but CodeChecker requires it to be " \
            "available. If you intend to hide the absolute path before " \
            "storing the results to a CodeChecker server, use " \
            "--trim-path-prefix."

        if not self.original_uri_base_ids:
            LOG.error("Missing 'originalUriBaseIds' (sarif v2.1.0 §3.14.14) "
                      "in '%s'.", self.result_file_path)
            LOG.error(error_str)
            self.had_error = True
            return ""

        original = self.original_uri_base_ids.get(uri_base_id)
        if not original:
            LOG.error("Missing entry for '%s in "
                      "'originalUriBaseIds' (sarif v2.1.0 §3.14.14) in '%s'.",
                      uri_base_id,
                      self.result_file_path)
            LOG.error(error_str)
            self.had_error = True
            return ""

        abs_uri_prefix = original.get("uri")
        if not abs_uri_prefix:
            LOG.warning("Missing 'uri' (sarif v2.1.0 §3.4.3) for "
                        "'%s in 'originalUriBaseIds' (sarif "
                        "v2.1.0 §3.14.14) in '%s'.",
                        uri_base_id,
                        self.result_file_path)
            LOG.error(error_str)
            self.had_error = True
            return ""

        if "uri_base_id" in original:
            prefix = self._resolve_uri_base_id(original.get("uri_base_id"),
                                               postfix)
            return prefix + abs_uri_prefix
        return abs_uri_prefix

    def _get_file(
        self,
        physical_loc: Dict
    ) -> Optional[File]:
        """
        Assemble the artifact location (§3.4) for physical_loc. Sarif files
        contain a lot of relative references, but also contains everything
        needed to resolve an absolute path for the file.
        """
        artifact_loc = physical_loc.get("artifactLocation")
        if not artifact_loc:
            return None

        uri = artifact_loc.get("uri")

        if "uriBaseId" in artifact_loc:
            uri = self._resolve_uri_base_id(
                    artifact_loc.get("uriBaseId"), uri) + uri

        uri_parsed = urlparse(uri)
        if uri_parsed is None:
            LOG.warning("Failed to urlparse %s!", uri)
            return None

        file_path = os.path.join(uri_parsed.netloc, uri_parsed.path)

        return get_or_create_file(file_path, self._file_cache)

    def _process_message(
        self,
        msg: Dict,
        rule_id: str,
        rules: Dict[str, Dict]
    ) -> str:
        """
        Parse message (§3.11). Sometimes, the warning message is attributed to
        the checker (or rule, as is called here) under messageStrings
        (§3.49.11), which might need a little extra parsing.
        """
        if "text" in msg:
            return msg["text"]

        args = msg.get("arguments", [])

        rule = rules[rule_id]
        message_strings = rule.get("messageStrings", {})
        return message_strings[msg["id"]]["text"].format(*args)

    def convert(
        self,
        reports: List[Report],
        analyzer_info: Optional[AnalyzerInfo] = None
    ):
        """ Converts the given reports to sarif format. """
        tool_name, tool_version = get_tool_info()

        rules = {}
        results = []
        for report in reports:
            if report.checker_name not in rules:
                rules[report.checker_name] = {
                    "id": report.checker_name,
                    "fullDescription": {
                        "text": report.message
                    }
                }

            results.append(self._create_result(report))

        return {
            "version": "2.1.0",
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/"
                       "sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": tool_name,
                        "version": tool_version,
                        "rules": list(rules.values())
                    }
                },
                "results": results
            }]
        }

    def _create_result(self, report: Report) -> Dict:
        """ Create result dictionary from the given report. """
        result = {
            "ruleId": report.checker_name,
            "message": {
                "text": report.message
            },
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": f"file://{report.file.original_path}"
                    },
                    "region": {
                        "startLine": report.line,
                        "startColumn": report.column
                    }
                }
            }]
        }

        locations = []

        if report.bug_path_events:
            for event in report.bug_path_events:
                locations.append(self._create_location_from_bug_path_event(
                    event, "important"))

        if report.notes:
            for note in report.notes:
                locations.append(self._create_location_from_bug_path_event(
                    note, "essential"))

        if report.macro_expansions:
            for macro_expansion in report.macro_expansions:
                locations.append(self._create_location_from_bug_path_event(
                    macro_expansion, "essential"))

        if report.bug_path_positions:
            for bug_path_position in report.bug_path_positions:
                locations.append(self._create_location(bug_path_position))

        if locations:
            result["codeFlows"] = [{
                "threadFlows": [{"locations": locations}]
            }]

        return result

    def _create_location_from_bug_path_event(
        self,
        event: BugPathEvent,
        importance: str
    ) -> Dict[str, Any]:
        """ Create location from bug path event. """
        location = self._create_location(event, event.line, event.column)

        location["importance"] = importance
        location["location"]["message"] = {"text": event.message}

        return location

    def _create_location(
        self,
        pos: BugPathPosition,
        line: Optional[int] = -1,
        column: Optional[int] = -1
    ) -> Dict[str, Any]:
        """ Create location from bug path position. """
        if pos.range:
            rng = pos.range
            region = {
                "startLine": rng.start_line,
                "startColumn": rng.start_col,
                "endLine": rng.end_line,
                "endColumn": rng.end_col,
            }
        else:
            # Seems like there is no smarter way to make mypy happy. Without
            # this trickery, it will complain about Optional[int] and int being
            # incompatible.
            assert line is not None
            assert column is not None
            linei: int = line
            columni: int = column
            region = {
                "startLine": linei,
                "startColumn": columni,
            }

        return {
            "location": {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": f"file://{pos.file.original_path}"
                    },
                    "region": region
                }
            }
        }

    def write(self, data: Any, output_file_path: str):
        """ Creates an analyzer output file from the given data. """
        try:
            with open(output_file_path, 'w',
                      encoding="utf-8", errors="ignore") as f:
                json.dump(data, f)
        except TypeError as err:
            LOG.error('Failed to write sarif file: %s', output_file_path)
            LOG.error(err)
            import traceback
            traceback.print_exc()

    def replace_report_hash(
        self,
        analyzer_result_file_path: str,
        hash_type=HashType.CONTEXT_FREE
    ):
        """
        Override hash in the given file by using the given version hash.
        """
