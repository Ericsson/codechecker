# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
import os
import re

from typing import Iterable, Optional, Tuple

from codechecker_report_converter.report import get_or_create_file, Report

from ...parser import get_next
from ..parser import SANParser


LOG = logging.getLogger('report-converter')


class Parser(SANParser):
    """ Parser for Clang UndefinedBehaviourSanitizer console outputs.

    Example output
        /a/b/main.cpp:13:10: runtime error: load of value 7...
    """

    checker_name = "UndefinedBehaviorSanitizer"

    # Regex for parsing UndefinedBehaviorSanitizer output message.
    line_re = re.compile(
        # File path followed by a ':'.
        r'^(?P<path>[\S ]+?):'
        # Line number followed by a ':'.
        r'(?P<line>\d+?):'
        # Column number followed by a ':' and a space.
        r'(?P<column>\d+?): runtime error: '
        # Checker message.
        r'(?P<message>[\S \t]+)')

    # This list of diagnostic messages is extracted from the LLVM project:
    #   https://github.com/llvm/llvm-project
    # /blob/main/compiler-rt/lib/ubsan/ubsan_handlers.cpp
    # /blob/main/compiler-rt/lib/ubsan/ubsan_handlers_cxx.cpp
    # /blob/main/compiler-rt/lib/ubsan/ubsan_checks.inc
    checks = {
        "alignment": [
            re.compile(
                ".* misaligned address .* for type .*, which requires .* byte "
                "alignment"),
            re.compile(
                "assumption of .* byte alignment for pointer of type .* "
                "failed"),
            re.compile(
                "assumption of .* byte alignment (with offset of .* byte) for "
                "pointer of type .* failed")],
        "bool": [
            re.compile(
                "load of value .*, which is not a valid value for type "
                ".*bool.*")],
        "builtin": [
            re.compile("passing zero to .*, which is not a valid argument")],
        "bounds": [
            re.compile("index .* out of bounds for type .*")],
        "enum": [
            re.compile(
                "load of value .*, which is not a valid value for type .*")],
        "float-cast-overflow": [
            re.compile(
                ".* is outside the range of representable values of type .*")],
        "integer-divide-by-zero-or-float-divide-by-zero": [
            re.compile("division by zero")],
        "implicit-signed-integer-truncation": [
            re.compile(
                "implicit conversion from type .* of value .* (.*-bit, "
                "signed) to type .* changed the value to .* (.*-bit, "
                "signed)")],
        "implicit-unsigned-integer-truncation": [
            re.compile(
                "implicit conversion from type .* of value .* (.*-bit, "
                "unsigned) to type .* changed the value to .* (.*-bit, "
                "unsigned)")],
        "implicit-integer-sign-change": [
            re.compile(
                "implicit conversion from type .* of value .* (.*-bit, "
                ".*signed) to type .* changed the value to .* (.*-bit, "
                ".*signed)")],
        "nonnull-attribute-or-nullability-arg": [
            re.compile(
                "null pointer passed as argument .*, which is declared to "
                "never be null")],
        "null-or-nullability-assign": [
            re.compile(".* null pointer of type .*")],
        "nullability-return-or-returns-nonnull-attribute": [
            re.compile(
                "null pointer returned from function declared to never return "
                "null")],
        "objc-cast": [
            re.compile(
                "invalid ObjC cast, object is a '.*', but expected a .*")],
        "object-size": [
            re.compile(
                ".* address .* with insufficient space for an object of type "
                ".*")],
        "pointer-overflow": [
            re.compile("applying zero offset to null pointer"),
            re.compile("applying non-zero offset .* to null pointer"),
            re.compile(
                "applying non-zero offset to non-null pointer .* produced "
                "null pointer"),
            re.compile("addition of unsigned offset to .* overflowed to .*"),
            re.compile(
                "subtraction of unsigned offset from .* overflowed to .*"),
            re.compile(
                "pointer index expression with base .* overflowed to .*")],
        "return": [
            re.compile(
                "execution reached the end of a value-returning function "
                "without returning a value")],
        "shift": [
            re.compile("shift exponent .* is negative"),
            re.compile("shift exponent .* is too large for .*-bit type .*"),
            re.compile("left shift of negative value .*")],
        "signed-integer-overflow": [
            re.compile(
                "signed integer overflow: .* .* .* cannot be represented in "
                "type .*"),
            re.compile(
                "negation of .* cannot be represented in type .*; cast to an "
                "unsigned type to negate this value to itself"),
            re.compile(
                "division of .* by -1 cannot be represented in type .*")],
        "unreachable": [
            re.compile("execution reached an unreachable program point")],
        "unsigned-integer-overflow": [
            re.compile(
                "unsigned integer overflow: .* .* .* cannot be represented "
                "in type .*"),
            re.compile("negation of .* cannot be represented in type .*"),
            re.compile(
                "left shift of .* by .* places cannot be represented in type "
                ".*")],
        "vla-bound": [
            re.compile(
                "variable length array bound evaluates to non-positive value "
                ".*")],
        "vptr": [
            re.compile(
                ".* address .* which does not point to an object of type .*")]
    }

    def parse_stack_trace(self, it, line):
        """ Iterate over lines and parse stack traces. """
        events = []
        stack_traces = []

        while self.stack_trace_re.match(line):
            event = self.parse_stack_trace_line(line)
            if event:
                events.append(event)

            stack_traces.append(line)
            line = get_next(it)

        events.reverse()

        return stack_traces, events, line

    def deduce_checker_name(self, message: str) -> str:
        for check, patterns in self.checks.items():
            if any(pattern.search(message) for pattern in patterns):
                return f"{self.checker_name}.{check}"
        return self.checker_name

    def parse_sanitizer_message(
        self,
        it: Iterable[str],
        line: str
    ) -> Tuple[Optional[Report], str]:
        """ Parses UndefinedBehaviorSanitizer output message. """
        match = self.line_re.match(line)
        if not match:
            return None, line

        report_file = get_or_create_file(
            os.path.abspath(match.group('path')), self._file_cache)
        report_line = int(match.group('line'))
        report_col = int(match.group('column'))

        line = get_next(it)
        stack_traces, events, line = self.parse_stack_trace(it, line)

        message = match.group('message').strip()
        checker_name = self.deduce_checker_name(message)

        report = self.create_report(
            events, report_file, report_line, report_col,
            message, stack_traces, checker_name)

        return report, line
