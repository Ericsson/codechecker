import unittest
import tempfile
import shutil
import plistlib
import os
import json

from codechecker_report_converter.analyzers.pvs_studio import analyzer_result
from codechecker_report_converter.report.parser import plist


class PvsStudioAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of PVS-Studio's AnalyzerResult. """

    def setUp(self) -> None:
        """ Set up the test. """
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.test_files = os.path.join(os.path.dirname(__file__),
                                       'pvs_studio_output_test_files')
        self.result_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        """Clean temporary directory. """
        shutil.rmtree(self.result_dir)

    def test_no_report_output_file(self) -> None:
        """ Test transforming single cpp file. """
        result = os.path.join(self.test_files, "files", "sample.cpp")

        is_success = self.analyzer_result.transform(
            analyzer_result_file_paths=[result],
            output_dir_path=self.result_dir,
            export_type=plist.EXTENSION,
            file_name="{source_file}_{analyzer}"
        )

        self.assertFalse(is_success)

    def test_transform_dir(self) -> None:
        """ Test transforming a directory. """
        result = os.path.join(self.test_files)

        is_success = self.analyzer_result.transform(
            analyzer_result_file_paths=[result],
            output_dir_path=self.result_dir,
            export_type=plist.EXTENSION,
            file_name="{source_file}_{analyzer}"
        )

        self.assertFalse(is_success)

    def test_transform_single_file(self) -> None:
        """ Test transforming single output file. """
        result = os.path.join(self.test_files, 'sample.json')

        self.make_report_valid()
        is_success = self.analyzer_result.transform(
            analyzer_result_file_paths=[result],
            output_dir_path=self.result_dir,
            export_type=plist.EXTENSION,
            file_name="{source_file}_{analyzer}"
        )

        self.assertTrue(is_success)

        plist_file = os.path.join(self.result_dir,
                                  'sample.cpp_pvs-studio.plist')

        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = os.path.join('files', 'sample.cpp')

        plist_file = os.path.join(self.test_files,
                                  'sample.plist')

        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)

    @staticmethod
    def make_report_valid() -> None:
        samples_path = os.path.join(
            os.path.dirname(__file__),
            "pvs_studio_output_test_files"
        )
        report_path = os.path.join(samples_path, "sample.json")
        with open(report_path, 'r') as file:
            data = json.loads(file.read())
            data["warnings"][0]["positions"][0]["file"] = os.path.join(
                samples_path,
                "files",
                "sample.cpp"
            )

        with open(report_path, "w") as file:
            file.write(json.dumps(data))


if __name__ == "__main__":
    unittest.main()
