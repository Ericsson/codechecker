import unittest

import libcodechecker.analyze.host_check as hc


class Test_has_analyzer_feature(unittest.TestCase):
    def test_existing_feature(self):
        self.assertEqual(
            hc.has_analyzer_feature("clang",
                                    "-analyzer-display-progress"),
            True)

    def test_non_existing_feature(self):
        self.assertEqual(
            hc.has_analyzer_feature("clang",
                                    "-non-existent-feature"),
            False)

    def test_non_existent_binary_throws(self):
        with self.assertRaises(OSError):
            hc.has_analyzer_feature("non-existent-binary-Yg4pEna5P7",
                                    "")
