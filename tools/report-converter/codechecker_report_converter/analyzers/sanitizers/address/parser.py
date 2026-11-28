# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
import re
from typing import Iterator

from codechecker_report_converter.report import BugPathEvent, Report

from ..parser import get_next, SANParser

LOG = logging.getLogger('report-converter')


class Parser(SANParser):
    """ Parser for Clang AddressSanitizer console outputs. """

    checker_name = "AddressSanitizer"

    line_re = re.compile(
        r'==(?P<code>\d+)==(ERROR|WARNING): AddressSanitizer: '
        r'(?P<message>[\S \t]+)')

    check_msg_pairs = {
        "double-free": re.compile(
            "attempting double-free on .* in thread .*:"),
        "new-delete-type-mismatch": re.compile(
            "new-delete-type-mismatch on .* in thread .*:"),
        "bad-free": re.compile(
            "attempting free on address which was not malloc()-ed: .* in "
            "thread .*"),
        "alloc-dealloc-mismatch": re.compile(
            "alloc-dealloc-mismatch (.* vs .*) on .*"),
        "bad-malloc_usable_size": re.compile(
            "attempting to call malloc_usable_size() for pointer which is not "
            "not owned: .*"),
        "bad-__sanitizer_get_allocated_size": re.compile(
            "attempting to call __sanitizer_get_allocated_size() for pointer "
            "which is not owned: .*"),
        "calloc-overflow": re.compile(
            "calloc parameters overflow: count * size (.* * .*) cannot be "
            "represented in type size_t (thread .*)"),
        "reallocarray-overflow": re.compile(
            "reallocarray parameters overflow: count * size (.* * .*) cannot "
            "be represented in type size_t (thread .*)"),
        "pvalloc-overflow": re.compile(
            "pvalloc parameters overflow: size 0x.* rounded up to system page "
            "size 0x.* cannot be represented in type size_t (thread .*)"),
        "invalid-allocation-alignment": re.compile(
            "invalid allocation alignment: .*, alignment must be a power of "
            "two (thread .*)"),
        "invalid-aligned-alloc-alignment": re.compile(
            "invalid alignment requested in aligned_alloc: .* the requested "
            "size 0x.* must be a multiple of alignment (thread .*)"),
        "invalid-posix-memalign-alignment": re.compile(
            "invalid alignment requested in posix_memalign: .*, alignment "
            "must be a power of two and a multiple of sizeof(void*) == .* "
            "(thread .*)"),
        "allocation-size-too-big": re.compile(
            "requested allocation size 0x.* (0x.* after adjustments for "
            "alignment, red zones etc.) exceeds maximum supported size of "
            "0x.* (thread .*)"),
        "rss-limit-exceeded": re.compile(
            "specified RSS limit exceeded, currently set to "
            "soft_rss_limit_mb=.*"),
        "out-of-memory": re.compile(
            "allocator is trying to allocate 0x.* bytes"),
        "string-function-memory-ranges-overlap": re.compile(
            ".*: memory ranges .* and .* overlap"),
        "negative-size-param": re.compile(
            "negative-size-param: (size=.*)"),
        "bad-__sanitizer_annotate_contiguous_container": re.compile(
            "bad parameters to __sanitizer_annotate_contiguous_container:"),
        "bad-__sanitizer_annotate_double_ended_contiguous_container":
        re.compile(
            "bad parameters to "
            "__sanitizer_annotate_double_ended_contiguous_container:"),
        "odr-violation": re.compile("odr-violation (.*):"),
        "invalid-pointer-pair": re.compile("invalid-pointer-pair: .* .*"),
        "generic-error": re.compile(".* on address .* at pc .* bp .* sp .*")
    }

    def deduce_checker_name(self, message: str) -> str:
        for check, pattern in self.check_msg_pairs.items():
            if pattern.search(message):
                return f"{self.checker_name}.{check}"
        return self.checker_name

    def parse_sanitizer_message(
        self,
        it: Iterator[str],
        line: str
    ) -> tuple[Report | None, str]:
        match = self.line_re.match(line)
        if not match:
            return None, line

        pid = match.group('code')
        message = match.group('message').strip()
        abort_marker = f"=={pid}==ABORTING"

        line = get_next(it)

        collected_lines: list[str] = []
        sections: list[tuple[str, list[BugPathEvent]]] = []

        current_header = ""
        current_events: list[BugPathEvent] = []

        while line:
            if line.startswith(abort_marker) or line.startswith("SUMMARY:"):
                collected_lines.append(line)
                break
            if self.line_re.match(line):
                break

            collected_lines.append(line)
            stripped = line.strip()

            if stripped:
                if (stripped.startswith("freed by thread") or
                        "allocated by thread" in stripped or
                        stripped.startswith("READ of size") or
                        stripped.startswith("WRITE of size") or
                        "is located" in stripped):
                    if current_events:
                        sections.append((current_header, current_events))
                        current_events = []
                    current_header = stripped
                else:
                    event = self.parse_stack_trace_line(line)
                    if event:
                        current_events.append(event)

            line = get_next(it)

        if current_events:
            sections.append((current_header, current_events))

        all_events = [ev for _, evs in sections for ev in evs]
        if not all_events:
            return None, line

        alloc_events: list[BugPathEvent] = []
        freed_events: list[BugPathEvent] = []
        crash_events: list[BugPathEvent] = []

        for header, evs in sections:
            evs.reverse()
            if "allocated by thread" in header:
                alloc_events.extend(evs)
            elif "freed by thread" in header:
                freed_events.extend(evs)
            else:
                crash_events.extend(evs)

        final_path_events: list[BugPathEvent] = []
        final_path_events.extend(alloc_events)
        final_path_events.extend(freed_events)
        final_path_events.extend(crash_events)

        main_event = (crash_events[-1]
                      if crash_events else all_events[self.main_event_index])

        report = self.create_report(
            final_path_events,
            main_event.file,
            main_event.line,
            main_event.column,
            message,
            collected_lines)

        report.checker_name = self.deduce_checker_name(report.message)

        return report, line
