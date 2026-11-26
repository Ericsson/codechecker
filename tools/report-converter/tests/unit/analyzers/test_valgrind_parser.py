# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Tests for converting Valgrind XML into CodeChecker reports."""

import io
import os
import plistlib
import tempfile
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape

from codechecker_report_converter.analyzers.valgrind.drd.parser import (
    Parser as DRDParser,
)
from codechecker_report_converter.analyzers.valgrind.helgrind.parser import (
    Parser as HelgrindParser,
)
from codechecker_report_converter.analyzers.valgrind.memcheck import (
    analyzer_result,
)
from codechecker_report_converter.analyzers.valgrind.memcheck.parser import (
    Parser as MemcheckParser,
)
from codechecker_report_converter.report.hash import (
    HashType,
    get_report_hash,
    get_report_path_hash,
)
from codechecker_report_converter.report.parser import plist


def frame(line, function, file=None):
    """Make a frame pointing to this test file."""
    file = file or os.path.abspath(__file__)
    return (f"<frame><ip>0x1</ip><fn>{function}</fn>"
            f"<file>{escape(file)}</file><line>{line}</line></frame>")


def document(tool, body):
    """Wrap records in a Valgrind protocol 6 document."""
    return (f'<?xml version="1.0"?><valgrindoutput>'
            f"<protocolversion>6</protocolversion>"
            f"<protocoltool>{tool}</protocoltool><args/>"
            f"{body}</valgrindoutput>").encode()


def parse(parser, xml, input_path="input.xml"):
    """Run the parser against in-memory XML."""
    with patch("builtins.open", return_value=io.BytesIO(xml)):
        return parser.get_reports(input_path)


class ValgrindParserTestCase(unittest.TestCase):
    """Check the shared parser and its three tool adapters."""

    def test_memcheck_reports(self):
        xml_path = os.path.join(os.path.dirname(__file__), "valgrind.xml")
        primary = (frame(7, "external", "vg_replace_malloc.c") +
                   frame(2, "fault", os.path.basename(__file__)) +
                   frame(1, "caller"))
        error = (
            "<error><kind>InvalidRead</kind>"
            "<what>Invalid read of size 4</what>"
            f"<stack>{primary}</stack>"
            "<auxwhat>Block was allocated at</auxwhat>"
            f"<stack>{frame(3, 'allocation')}</stack>"
            "<suppression><sname>ignore me</sname></suppression></error>"
        )
        fd_error = (
            "<error><path>/tmp/file</path><kind>FdBadClose</kind>"
            "<what>Bad close of file descriptor 3</what>"
            f"<stack>{frame(2, 'fault')}</stack><fd>3</fd></error>"
        )
        reports = parse(MemcheckParser("memcheck"),
                        document("memcheck", error + fd_error), xml_path)

        self.assertEqual(len(reports), 2)
        report = reports[0]
        self.assertEqual(report.file.original_path, os.path.abspath(__file__))
        self.assertEqual((report.line, report.column), (2, 0))
        self.assertEqual([event.line for event in report.bug_path_events],
                         [1, 2])
        self.assertEqual(report.message, "Invalid Read")
        self.assertEqual(report.bug_path_events[-1].message, report.message)
        self.assertEqual(len(report.notes), 1)
        self.assertIn("Invalid read of size 4", report.notes[0].message)
        self.assertIn("Block was allocated at", report.notes[0].message)
        self.assertIn("allocation", report.notes[0].message)
        self.assertNotIn("ignore me", report.notes[0].message)

        self.assertEqual(reports[1].checker_name, "Memcheck.FdBadClose")
        self.assertIn("FD 3, /tmp/file", reports[1].notes[0].message)

    def test_hash_ignores_changing_details(self):
        def report(kind, detail):
            error = (f"<error><kind>{kind}</kind><what>{detail}</what>"
                     f"<stack>{frame(2, 'fault')}</stack></error>")
            return parse(MemcheckParser("memcheck"),
                         document("memcheck", error))[0]

        first = report("InvalidRead", "Invalid read at 0x1234 of size 4")
        second = report("InvalidRead", "Invalid read at 0x5678 of size 8")
        different = report("InvalidWrite", "Invalid write at 0x1234")

        self.assertEqual(first.static_message, "Memcheck.InvalidRead")
        self.assertEqual(first.message, first.bug_path_events[-1].message)
        self.assertEqual(
            get_report_hash(first, HashType.CONTEXT_FREE),
            get_report_hash(second, HashType.CONTEXT_FREE))
        self.assertEqual(get_report_path_hash(first),
                         get_report_path_hash(second))
        self.assertNotEqual(
            get_report_hash(first, HashType.CONTEXT_FREE),
            get_report_hash(different, HashType.CONTEXT_FREE))
        self.assertIn("0x1234", first.notes[0].message)

    def test_helgrind_threads_and_fatal_signal(self):
        stack = f"<stack>{frame(2, 'fault')}</stack>"
        announcement = (
            f"<announcethread><hthreadid>2</hthreadid>{stack}"
            "</announcethread>"
        )
        error = (
            "<error><kind>Race</kind>"
            "<xwhat><text>Race at 0x1234</text>"
            f"<hthreadid>2</hthreadid></xwhat>{stack}</error>"
        )
        fatal_signal = (
            "<fatal_signal><signame>SIGSEGV</signame>"
            "<event>SEGV_MAPERR</event><siaddr>0x1234</siaddr>"
            f"{stack}</fatal_signal>"
        )
        reports = parse(HelgrindParser("helgrind"),
                        document("helgrind", announcement + error +
                                 fatal_signal))

        self.assertEqual([report.checker_name for report in reports],
                         ["Helgrind.Race",
                          "Helgrind.FatalSignal.SIGSEGV"])
        self.assertIn("Thread 2 created at", reports[0].notes[0].message)
        self.assertEqual(reports[1].message, "Fatal signal SIGSEGV")
        self.assertIn("Signal event: SEGV_MAPERR",
                      reports[1].notes[0].message)
        self.assertIn("Signal address: 0x1234",
                      reports[1].notes[0].message)

    def test_drd_related_stacks(self):
        stack = f"<stack>{frame(2, 'fault')}</stack>"
        related = f"<stack>{frame(3, 'related')}</stack>"
        error = (
            "<error><kind>ConflictingAccess</kind>"
            f"<what>Conflicting access</what>{stack}"
            "<first_observed_at>"
            "<what>mutex was first observed at</what>"
            "<address>0x1234</address>"
            f"{related}</first_observed_at>"
            f"<future_context>{related}</future_context>"
            f"<suppression>{related}</suppression></error>"
        )
        reports = parse(DRDParser("drd"), document("drd", error))

        self.assertEqual(len(reports), 1)
        note = reports[0].notes[0].message
        self.assertIn("mutex was first observed at", note)
        self.assertIn("Address: 0x1234", note)
        self.assertIn("first observed at: related", note)
        self.assertIn("future context: related", note)
        self.assertNotIn("suppression", note)

    def test_rejects_invalid_xml(self):
        valid = document("memcheck", "")
        error = (f"<error><kind>InvalidRead</kind><what>Invalid read</what>"
                 f"<stack>{frame(2, 'fault')}</stack></error>")
        invalid = (
            valid.replace(b'<?xml version="1.0"?>', b""),
            valid.replace(b"<valgrindoutput>",
                          b"<!DOCTYPE valgrindoutput><valgrindoutput>"),
            valid.replace(b"<protocolversion>6</protocolversion>",
                          b"<protocolversion>3</protocolversion>"),
            valid.replace(b"<protocoltool>memcheck</protocoltool>",
                          b"<protocoltool>helgrind</protocoltool>"),
            valid.replace(b"<args/>", b""),
            document("memcheck", error) + b"<extra/>",
        )
        for xml in invalid:
            with self.subTest(xml=xml[:80]):
                with self.assertLogs("report-converter", level="WARNING"):
                    self.assertEqual(
                        parse(MemcheckParser("memcheck"), xml), [])

    def test_transform_writes_plist(self):
        error = (f"<error><kind>InvalidRead</kind>"
                 f"<what>Invalid read</what>"
                 f"<stack>{frame(2, 'fault')}</stack></error>")
        with tempfile.TemporaryDirectory() as directory:
            xml_path = os.path.join(directory, "valgrind.xml")
            output_dir = os.path.join(directory, "reports")
            os.mkdir(output_dir)
            with open(xml_path, "wb") as stream:
                stream.write(document("memcheck", error))

            converted = analyzer_result.AnalyzerResult().transform(
                [xml_path], output_dir, plist.EXTENSION,
                file_name="{source_file}_{analyzer}",
                metadata={"analyzer_version": "test"})
            self.assertTrue(converted)

            output_path = os.path.join(
                output_dir, f"{os.path.basename(__file__)}_memcheck.plist")
            with open(output_path, "rb") as stream:
                result = plistlib.load(stream)

            self.assertEqual(len(result["diagnostics"]), 1)
            diagnostic = result["diagnostics"][0]
            self.assertEqual(diagnostic["check_name"],
                             "Memcheck.InvalidRead")
            self.assertEqual(diagnostic["description"], "Invalid Read")
            self.assertTrue(
                diagnostic["issue_hash_content_of_line_in_context"])


if __name__ == "__main__":
    unittest.main()
