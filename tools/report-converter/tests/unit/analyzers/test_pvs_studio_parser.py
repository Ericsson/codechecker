import unittest
import tempfile
import shutil
import plistlib
import os


from codechecker_report_converter.analyzers.pvs_studio import analyzer_result


class PvsStudioAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of PVS-Studio's AnalyzerResult. """

    def setUp(self):
        """ Set up the test. """
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(os.path.dirname(__file__),
                                       'pvs_studio_output_test_files')

    def tearDown(self):
        """Clean temporary directory. """
        shutil.rmtree(self.result_dir)

    def test_no_report_output_file(self):
        """ Test transforming single cpp file. """
        result = os.path.join(self.test_files, "files", "sample.cpp")

        is_success = self.analyzer_result.transform(
            [result], self.result_dir,
            file_name="{source_file}_{analyzer}"
        )

        self.assertFalse(is_success)

    def test_transform_dir(self):
        """ Test transforming a directory. """
        result = os.path.join(self.test_files)

        is_success = self.analyzer_result.transform(
            [result],
            self.result_dir,
            file_name="{source_file}_{analyzer}"
        )

        self.assertFalse(is_success)

    def test_transform_single_file(self):
        """ Test transforming single output file. """
        analyzer_result = os.path.join(self.test_files, 'sample.out')
        self.analyzer_result.transform(
            [analyzer_result], self.result_dir,
            file_name="{source_file}_{analyzer}")

        plist_file = os.path.join(self.result_dir,
                                  'sample.plist')

        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = os.path.join('files', 'sample.cpp')

        plist_file = os.path.join(self.test_files,
                                  'sample.plist')

        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)
