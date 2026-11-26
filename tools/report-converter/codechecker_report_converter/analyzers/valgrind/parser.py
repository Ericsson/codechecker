# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Shared Valgrind XML parser; tool adapters allow future extensions."""

import logging
import os
import re
import xml.etree.ElementTree as ET

from codechecker_report_converter.report import (
    BugPathEvent,
    File,
    Report,
    get_or_create_file,
)

LOG = logging.getLogger("report-converter")

# Require the XML declaration and root within 4096 bytes before
# Expat sees the file. This also rejects DTDs before the root.
_XML_OPENING_PATTERN = re.compile(
    rb"^(?:\xef\xbb\xbf)?<\?xml\s+version=[\"']1\.0[\"']"
    rb"(?:\s+encoding=[\"'][uU][tT][fF]-8[\"'])?\s*\?>"
    rb"\s*<valgrindoutput>"
)


class ValgrindParser:
    """Convert protocol 4–6 records; tool adapters supply their identity."""

    checker_name_prefix = ""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name

    def get_reports(self, input_path: str) -> list[Report]:
        """Parse one XML file; the CLI handles directory expansion."""
        reports: list[Report] = []
        source_file_cache: dict[str, File] = {}
        # Helgrind announces a thread's creation stack before referencing it.
        thread_announcements: dict[str, str] = {}

        try:
            with open(input_path, "rb") as stream:
                if not _XML_OPENING_PATTERN.match(stream.read(4096)):
                    LOG.warning(
                        "Not a supported Valgrind XML file: %s", input_path
                    )
                    return []
                stream.seek(0)

                event_stream = ET.iterparse(stream, events=("start", "end"))
                event_type, root = next(event_stream)
                if event_type != "start" or root.tag != "valgrindoutput":
                    return []

                top_level_elements = self._top_level_elements(
                    event_stream, root
                )

                if not self._read_header(top_level_elements):
                    LOG.warning("Invalid Valgrind header in %s", input_path)
                    return []

                for element in top_level_elements:
                    if element.tag == "announcethread":
                        thread_id = (
                            element.findtext("hthreadid") or ""
                        ).strip()
                        stack = element.find("stack")
                        if thread_id and stack is not None:
                            thread_announcements[thread_id] = (
                                self._stack_location(
                                    stack, input_path, source_file_cache
                                )
                            )
                    elif element.tag in ("error", "fatal_signal"):
                        report = self._build_report(
                            element,
                            input_path,
                            source_file_cache,
                            thread_announcements,
                        )
                        if report is not None:
                            reports.append(report)

        except (OSError, ET.ParseError) as error:
            LOG.warning(
                "Could not parse Valgrind XML %s: %s", input_path, error
            )
            return []

        return reports

    @staticmethod
    def _top_level_elements(event_stream, root: ET.Element):
        """Yield each complete element directly under the root."""
        depth = 0
        for event_type, element in event_stream:
            if event_type == "start":
                depth += 1
            elif element is root:
                # Keep reading so the XML parser can reject trailing junk.
                continue
            else:
                if depth == 1:
                    yield element
                    # This runs when the caller asks for the next child.
                    element.clear()
                    root.clear()
                depth -= 1

    def _read_header(self, top_level_elements) -> bool:
        """Check the first two fields, then skip metadata through <args>."""
        version = next(top_level_elements, None)
        if (
            version is None
            or version.tag != "protocolversion"
            or (version.text or "").strip() not in ("4", "5", "6")
        ):
            return False

        tool = next(top_level_elements, None)
        if (
            tool is None
            or tool.tag != "protocoltool"
            or (tool.text or "").strip() != self.tool_name
        ):
            return False

        for element in top_level_elements:
            if element.tag == "args":
                return True
            if element.tag in ("error", "fatal_signal", "announcethread"):
                return False
        return False

    def _stack_location(
        self,
        stack: ET.Element,
        input_path: str,
        source_file_cache: dict[str, File],
    ) -> str:
        """Use the nearest local source frame, or the first available frame."""
        locations = self._usable_locations_from_stack(
            stack, input_path, source_file_cache
        )
        if locations:
            source_file, function, line = locations[0]
            place = f"{source_file.original_path}:{line}"
            return f"{function} ({place})" if function else place

        frame = stack.find("frame")
        if frame is None:
            return ""
        function = frame.findtext("fn") or ""
        file = frame.findtext("file")
        if file:
            place = os.path.join(frame.findtext("dir") or "", file)
            line_text = frame.findtext("line")
            if line_text:
                place = f"{place}:{line_text}"
        else:
            place = frame.findtext("obj") or frame.findtext("ip") or ""
        if function and place:
            return f"{function} ({place})"
        return function or place

    def _usable_locations_from_stack(
        self,
        stack: ET.Element,
        input_path: str,
        source_file_cache: dict[str, File],
    ) -> list[tuple[File, str, int]]:
        """Return usable (File, function, line) values, fault first."""
        usable_locations = []
        for frame in stack.findall("frame"):
            usable_location = self._usable_location_from_frame(
                frame, input_path, source_file_cache
            )
            if usable_location is not None:
                usable_locations.append(usable_location)
        return usable_locations

    @staticmethod
    def _usable_location_from_frame(
        frame: ET.Element, input_path: str, source_file_cache: dict[str, File]
    ) -> tuple[File, str, int] | None:
        """Return (File, function, line) if the source file exists."""
        file = frame.findtext("file")
        line_text = frame.findtext("line")
        if not file or not line_text:
            return None

        try:
            line = int(line_text)
        except ValueError:
            return None
        if line < 1:
            return None

        source_path = os.path.join(frame.findtext("dir") or "", file)
        if not os.path.isabs(source_path):
            path_beside_xml = os.path.join(
                os.path.dirname(input_path), source_path
            )
            if os.path.isfile(path_beside_xml):
                source_path = path_beside_xml

        source_path = os.path.abspath(source_path)
        if not os.path.isfile(source_path):
            return None

        source_file = get_or_create_file(source_path, source_file_cache)
        function = frame.findtext("fn") or ""
        return source_file, function, line

    def _build_report(
        self,
        finding: ET.Element,
        input_path: str,
        source_file_cache: dict[str, File],
        thread_announcements: dict[str, str],
    ) -> Report | None:
        """Build one report from an error or fatal signal."""
        primary_stack = finding.find("stack")
        if primary_stack is None:
            return None

        if finding.tag == "fatal_signal":
            fatal_signal_name = (finding.findtext("signame") or "").strip()
            if not fatal_signal_name:
                fatal_signal_name = "Unknown"
            checker_name = (
                f"{self.checker_name_prefix}.FatalSignal.{fatal_signal_name}"
            )
            message = f"Fatal signal {fatal_signal_name}"
        else:
            kind = (finding.findtext("kind") or "").strip()
            if not kind:
                return None
            checker_name = f"{self.checker_name_prefix}.{kind}"
            # Use the kind for the stable main message.
            message = re.sub(
                r"(?<=[a-z])(?=[A-Z])", " ", kind.replace("_", " ")
            )

        usable_locations = self._usable_locations_from_stack(
            primary_stack, input_path, source_file_cache
        )
        if not usable_locations:
            LOG.debug(
                "No local source location for %s in %s",
                checker_name,
                input_path,
            )
            return None

        # Valgrind lists the fault first.
        report_file, _, report_line = usable_locations[0]

        # Valgrind has no stable column or cross-run <unique> ID. Same-kind
        # findings on one line share a report hash,
        # so CodeChecker cannot distinguish those cases.
        static_message = checker_name

        bug_path_events = []
        for source_file, function, source_line in reversed(
            usable_locations[1:]
        ):
            event_message = f"In {function}" if function else "In caller"
            bug_path_events.append(
                BugPathEvent(event_message, source_file, source_line, 0)
            )
        bug_path_events.append(
            BugPathEvent(message, report_file, report_line, 0)
        )

        # Group details into one note to avoid a bubble for every XML field.
        note_messages: list[str] = []

        for element in finding:
            if element.tag == "suppression":
                continue
            if element.tag in ("what", "auxwhat"):
                detail = (element.text or "").strip()
                if detail:
                    note_messages.append(detail)
            elif element.tag in ("xwhat", "xauxwhat"):
                detail = (element.findtext("text") or "").strip()
                if detail:
                    note_messages.append(detail)
            elif element.tag == "event":
                detail = (element.text or "").strip()
                if detail:
                    note_messages.append(f"Signal event: {detail}")
            elif element.tag == "siaddr":
                detail = (element.text or "").strip()
                if detail:
                    note_messages.append(f"Signal address: {detail}")

            for context_field in element:
                if context_field.tag in ("what", "address"):
                    value = (context_field.text or "").strip()
                    if value:
                        if context_field.tag == "address":
                            note_messages.append(f"Address: {value}")
                        else:
                            note_messages.append(value)

            for stack in element.iter("stack"):
                if stack is primary_stack:
                    continue
                location = self._stack_location(
                    stack, input_path, source_file_cache
                )
                if location:
                    label = (
                        "Related stack"
                        if element is stack
                        else element.tag.replace("_", " ")
                    )
                    note_messages.append(f"{label}: {location}")

        fd = finding.findtext("fd")
        path = finding.findtext("path")
        if fd or path:
            details = ", ".join(
                part for part in (f"FD {fd}" if fd else "", path or "") if part
            )
            note_messages.append(details)

        seen_threads = set()
        for reference in finding.iter("hthreadid"):
            thread_id = (reference.text or "").strip()
            if not thread_id or thread_id in seen_threads:
                continue
            seen_threads.add(thread_id)
            creation = thread_announcements.get(thread_id)
            if creation:
                note_messages.append(
                    f"Thread {thread_id} created at: {creation}"
                )

        notes = []
        if note_messages:
            notes.append(
                BugPathEvent(
                    "\n".join(note_messages), report_file, report_line, 0
                )
            )

        return Report(
            report_file,
            report_line,
            0,
            message,
            checker_name,
            static_message=static_message,
            bug_path_events=bug_path_events,
            notes=notes,
        )
