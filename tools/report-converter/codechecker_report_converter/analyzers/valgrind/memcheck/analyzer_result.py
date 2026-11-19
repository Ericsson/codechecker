# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from codechecker_report_converter.report import Report

from ...analyzer_result import AnalyzerResultBase
from .parser import Parser


class AnalyzerResult(AnalyzerResultBase):
    """Transform analyzer result of Valgrind Memcheck."""

    TOOL_NAME = "memcheck"
    NAME = "Valgrind Memcheck"
    URL = "https://valgrind.org/docs/manual/mc-manual.html"
    EXAMPLE_CMD = (
        "# Choose ONE Valgrind command for how ./program creates children.\n"
        "# Use a fresh vg_out directory for each run.\n"
        "mkdir -p vg_out\n\n"
        "# Single process, or ignore child processes:\n"
        "valgrind -q --tool=memcheck --leak-check=full --xml=yes \\\n"
        '  --xml-file="$PWD/vg_out/vg-%p.xml" \\\n'
        "  --child-silent-after-fork=yes ./program\n\n"
        "# Include children that call exec; pure-fork workers stay silent:\n"
        "valgrind -q --tool=memcheck --leak-check=full --xml=yes \\\n"
        '  --xml-file="$PWD/vg_out/vg-%p.xml" \\\n'
        "  --trace-children=yes --child-silent-after-fork=yes ./program\n\n"
        "# Include pure-fork workers that do not call exec:\n"
        "valgrind -q --tool=memcheck --leak-check=full --xml=yes \\\n"
        '  --xml-file="$PWD/vg_out/vg-%p.xml" \\\n'
        "  --child-silent-after-fork=no ./program\n\n"
        "report-converter -t memcheck -o ./reports ./vg_out"
    )

    def get_reports(self, file_path: str) -> list[Report]:
        return Parser(self.TOOL_NAME).get_reports(file_path)
