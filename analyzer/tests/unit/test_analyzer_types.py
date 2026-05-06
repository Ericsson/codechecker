# coding=utf-8
"""
Unit tests for analyzer type helper functions.
"""

from unittest import mock

from codechecker_analyzer.analyzers import analyzer_types


class FakeProcess:
    """Fake subprocess object for clang-apply-replacements --help."""

    def __init__(self, stdout_text, stderr_text):
        self._stdout_text = stdout_text
        self._stderr_text = stderr_text

    def communicate(self):
        return self._stdout_text, self._stderr_text


class FakeContext:
    """Fake analyzer context with a configured replacer binary."""

    replacer_binary = "clang-apply-replacements"

    def get_env_for_bin(self, _binary):
        return {}


def test_ignore_insert_conflict_detected_from_stderr():
    """The flag should be detected even if help text is printed to stderr."""

    with mock.patch.object(
        analyzer_types.analyzer_context,
        "get_context",
        return_value=FakeContext()
    ), mock.patch.object(
        analyzer_types.subprocess,
        "Popen",
        return_value=FakeProcess("", "--ignore-insert-conflict")
    ):
        assert analyzer_types.is_ignore_conflict_supported()


def test_ignore_insert_conflict_detected_from_stdout():
    """The flag should still be detected from stdout."""

    with mock.patch.object(
        analyzer_types.analyzer_context,
        "get_context",
        return_value=FakeContext()
    ), mock.patch.object(
        analyzer_types.subprocess,
        "Popen",
        return_value=FakeProcess("--ignore-insert-conflict", "")
    ):
        assert analyzer_types.is_ignore_conflict_supported()
