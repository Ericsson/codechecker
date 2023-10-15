import unittest
import io
import contextlib

from codechecker_report_converter.report.statistics import Statistics


class TestCheckerSummary(unittest.TestCase):
    """ Test the output of the statistics checker summary. """

    def test_checker_summary(self):
        """ Test the output of the statistics checker summary. """
        input = {"Checker_A": 1, "Checker_B": 2, "Checker_C": 3}
        Statistics.write_checker_summary(input)
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            Statistics.write_checker_summary(input, f)
            output = f.getvalue()
        self.assertIn("Checker_C    | 3", output)
        self.assertIn("Checker_B    | 2", output)
        self.assertIn("Checker_A    | 1", output)

        # Check if checker_C comes first in the output
        self.assertLess(output.find("Checker_C"), output.find("Checker_B"))
