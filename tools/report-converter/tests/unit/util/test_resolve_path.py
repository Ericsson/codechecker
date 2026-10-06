import os
import shutil
import tempfile
import unittest

from codechecker_report_converter.util import resolve_path


class TestResolvePath(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.real_dir = os.path.join(self.test_dir, "real_dir", "headers")
        os.makedirs(self.real_dir, exist_ok=True)

        self.target_file = os.path.join(self.real_dir, "header.h")
        with open(self.target_file, "w", encoding="utf-8") as f:
            f.write("// header\n")

        self.symlink_dir = os.path.join(self.test_dir, "symlink_dir")
        os.symlink(self.real_dir, self.symlink_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_symlink_parent_traversal(self):
        tricky_path = os.path.join(self.symlink_dir, "..", "headers", "header.h")

        norm = os.path.normpath(tricky_path)
        self.assertFalse(os.path.exists(norm))

        resolved = resolve_path(tricky_path)
        self.assertTrue(os.path.exists(resolved))
        self.assertEqual(os.path.realpath(self.target_file), os.path.realpath(resolved))

    def test_nonexistent_path_fallback(self):
        non_existent = "/path/that/does/not/exist/foo/../bar"
        self.assertEqual(resolve_path(non_existent), os.path.normpath(non_existent))

    def test_empty_path(self):
        self.assertEqual(resolve_path(""), "")


if __name__ == "__main__":
    unittest.main()
