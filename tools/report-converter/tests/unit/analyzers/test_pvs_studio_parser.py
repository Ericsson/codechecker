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
        self.test_files = os.path.join(
            os.path.dirname(__file__),
            'pvs_studio_output_test_files'
        )
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
        self.make_report_valid()
        result = os.path.join(self.test_files, 'sample.json')

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

        plist_file = os.path.join(self.test_files,
                                  'sample.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(
            res["diagnostics"][0]["check_name"],
            exp["diagnostics"][0]["check_name"]
        )

        self.assertEqual(
            res["diagnostics"][0]["location"]["line"],
            exp["diagnostics"][0]["location"]["line"]
        )

        self.assertEqual(
            res["diagnostics"][0]["issue_hash_content_of_line_in_context"],
            exp["diagnostics"][0]["issue_hash_content_of_line_in_context"]
        )

    @staticmethod
    def make_report_valid() -> None:
        """ The method sets absolute paths in PVS-Studio report
        and .plist sample. """

        samples_path = os.path.join(
            os.path.dirname(__file__),
            "pvs_studio_output_test_files"
        )

        path_to_file = os.path.join(
            samples_path,
            "files",
            "sample.cpp"
        )

        report_path = os.path.join(samples_path, "sample.json")
        with open(report_path, 'r', encoding="utf-8") as file:
            data = json.loads(file.read())
            data["warnings"][0]["positions"][0]["file"] = path_to_file

        with open(report_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(data))

        path_to_plist = os.path.join(samples_path, "sample.plist")

        with open(path_to_plist, "rb") as plist_file:
            data = plistlib.load(plist_file)
            data["files"][0] = path_to_file

        with open(path_to_plist, "wb") as plist_file:
            plistlib.dump(data, plist_file)


if __name__ == "__main__":
    unittest.main()
