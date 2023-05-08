# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import logging
import re
from typing import Iterator, Optional, Tuple

from codechecker_report_converter.report import Report

from ..parser import SANParser

LOG = logging.getLogger('report-converter')


class Parser(SANParser):
    """ Parser for Clang AddressSanitizer console outputs. """

    checker_name = "AddressSanitizer"

    # Regex for parsing AddressSanitizer output message.
    line_re = re.compile(
            # Error code
            r'==(?P<code>\d+)==(ERROR|WARNING): AddressSanitizer: '
            # Checker message.
            r'(?P<message>[\S \t]+)')

    check_msg_pairs = {
        "double-free": re.compile(
            "attempting double-free on .+ in thread .+:"),
        "new-delete-type-mismatch": re.compile(
            "new-delete-type-mismatch on .+ in thread .+:"),
        "bad-free": re.compile(
            "attempting free on address which was not malloc()-ed: .+ in "
            "thread .+"),
        "alloc-dealloc-mismatch": re.compile(
            "alloc-dealloc-mismatch (.+ vs .+) on .+"),
        "bad-malloc_usable_size": re.compile(
            "attempting to call malloc_usable_size() for pointer which is not "
            "not owned: .+"),
        "bad-__sanitizer_get_allocated_size": re.compile(
            "attempting to call __sanitizer_get_allocated_size() for pointer "
            "which is not owned: .+"),
        "calloc-overflow": re.compile(
            "calloc parameters overflow: count * size (.+ * .+) cannot be "
            "represented in type size_t (thread .+)"),
        "reallocarray-overflow": re.compile(
            "reallocarray parameters overflow: count * size (.+ * .+) cannot "
            "be represented in type size_t (thread .+)"),
        "pvalloc-overflow": re.compile(
            "pvalloc parameters overflow: size 0x.+ rounded up to system page "
            "size 0x.+ cannot be represented in type size_t (thread .+)"),
        "invalid-allocation-alignment": re.compile(
            "invalid allocation alignment: .+, alignment must be a power of "
            "two (thread .+)"),
        "invalid-aligned-alloc-alignment": re.compile(
            "invalid alignment requested in aligned_alloc: .+ the requested "
            "size 0x.+ must be a multiple of alignment (thread .+)"),
        "invalid-posix-memalign-alignment": re.compile(
            "invalid alignment requested in posix_memalign: .+, alignment "
            "must be a power of two and a multiple of sizeof(void*) == .+ "
            "(thread .+)"),
        "allocation-size-too-big": re.compile(
            "requested allocation size 0x.+ (0x.+ after adjustments for "
            "alignment, red zones etc.) exceeds maximum supported size of "
            "0x.+ (thread .+)"),
        "rss-limit-exceeded": re.compile(
            "specified RSS limit exceeded, currently set to "
            "soft_rss_limit_mb=.+"),
        "out-of-memory": re.compile(
            "allocator is trying to allocate 0x.+ bytes"),
        "string-function-memory-ranges-overlap": re.compile(
            ".+: memory ranges .+ and .+ overlap"),
        "negative-size-param": re.compile(
            "negative-size-param: (size=.+)"),
        "bad-__sanitizer_annotate_contiguous_container": re.compile(
            "bad parameters to __sanitizer_annotate_contiguous_container:"),
        "bad-__sanitizer_annotate_double_ended_contiguous_container":
        re.compile(
            "bad parameters to "
            "__sanitizer_annotate_double_ended_contiguous_container:"),
        "odr-violation": re.compile("odr-violation (.+):"),
        "invalid-pointer-pair": re.compile("invalid-pointer-pair: .+ .+")
    }

    def parse_sanitizer_message(
        self,
        it: Iterator[str],
        line: str
    ) -> Tuple[Optional[Report], str]:
        report, line = super().parse_sanitizer_message(it, line)

        if not report:
            return report, line

        for check, pattern in self.check_msg_pairs.items():
            if pattern.search(report.message):
                report.checker_name = f"{self.checker_name}.{check}"
                break

        return report, line
