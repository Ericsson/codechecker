# cc_binary for simple C++ tests
load(
    "@rules_cc//cc:defs.bzl",
    "cc_binary",
    "cc_library",
)

# compile_commands rule
load(
    "@bazel_codechecker//src:compile_commands.bzl",
    "compile_commands",
)

# codechecker rules
load(
    "@bazel_codechecker//src:codechecker.bzl",
    "codechecker",
    "codechecker_config",
    "codechecker_suite",
    "codechecker_test",
)

# clang-tidy and clang -analyze rules
load(
    "@bazel_codechecker//src:clang.bzl",
    "clang_analyze_test",
    "clang_tidy_test",
)

# clang -analyze + CTU rule
load(
    "@bazel_codechecker//src:clang_ctu.bzl",
    "clang_ctu_test",
)

# Prototype for CodeChecker analyze --file
# NOTE: CodeChecker analyze --file --ctu does not work
load(
    "@bazel_codechecker//src:code_checker.bzl",
    "code_checker_test",
)

# Test for strip_include_prefix
cc_library(
    name = "test_inc",
    hdrs = glob(["inc/*.h"]),
    # NOTE: the following is for test purpose only
    # NOTE: use includes instead of strip_include_prefix
    strip_include_prefix = "inc",
)

# Test defect in transitive dependencies
cc_library(
    name = "test_lib",
    srcs = ["src/lib.cc"],
)

# Test defect in CTU mode
cc_library(
    name = "test_ctu",
    srcs = ["src/ctu.cc"],
)

# Simplest C++ test which should PASS
cc_binary(
    name = "test_pass",
    srcs = ["src/pass.cc"],
    deps = ["test_inc"],
)

# Simplest C++ test which should FAIL
cc_binary(
    name = "test_fail",
    srcs = ["src/fail.cc"],
    deps = [
        "test_ctu",
        "test_inc",
        "test_lib",
    ],
)

# Generate compile_commands.json file for host test
compile_commands(
    name = "compile_commands_pass",
    targets = [
        ":test_pass",
    ],
)

# CodeChecker configuration options specification
# based on Bazel configuration approach
codechecker_config(
    name = "codechecker_config",
    analyze = [
        "--disable=profile:default",
        "--enable=core",
        "--enable=bugprone-dangling-handle",
        "--enable=bugprone-fold-init-type",
        "--enable=misc-non-copyable-objects",
        "--report-hash=context-free-v2",
    ],
    # env = CODECHECKER_ENV,
    parse = [
        "--print-step",
    ],
)

# CodeChecker configuration file in JSON format
filegroup(
    name = "codechecker_config_file",
    srcs = [":config.json"],
)

# CodeChecker configuration options specification
# using JSON configuration file based approach,
# inherently supported by CodeChecker
codechecker_config(
    name = "codechecker_config_json",
    config_file = "codechecker_config_file",
)

# Simple codechecker rule - performs only "build" phase without "test"
codechecker(
    name = "codechecker_pass_build",
    config = "codechecker_config_json",
    targets = [
        "test_pass",
    ],
)

# Simplest codechecker_test example
# Runs CodeChecker on "test_pass" target
codechecker_test(
    name = "codechecker_pass",
    analyze = [
        "--ctu",
    ],
    config = "codechecker_config_json",
    targets = [
        "test_pass",
    ],
)

# This codechecker_test example supposed to fail showing findings report
# Note "manual" tag (means should not be run with other tests)
codechecker_test(
    name = "codechecker_fail",
    tags = [
        "manual",
    ],
    targets = [
        "test_fail",
    ],
)

# This codechecker_test CTU example supposed to fail showing findings report
# Note "manual" tag (means should not be run with other tests)
codechecker_test(
    name = "codechecker_ctu",
    analyze = [
        "--ctu",
    ],
    tags = [
        "manual",
    ],
    targets = [
        "test_fail",
    ],
)

# Simplest codechecker_suite example for "test_pass"
# Can run CodeChecker on targets built for different platforms
# This example performs build for just default platform i.e gcc
codechecker_suite(
    name = "codechecker_pass_multi",
    config = "codechecker_config_json",
    # platforms = [
    #     "@platforms//os:linux",
    #     "@platforms//os:ios",
    #     "@platforms//os:android",
    # ],
    targets = [
        "test_pass",
    ],
)

# This simple clang-tidy test should pass
clang_tidy_test(
    name = "clang_tidy_pass",
    targets = [
        "test_pass",
    ],
)

# And this clang-tidy test should fail
# Note "manual" tag (means should not be run with other tests)
clang_tidy_test(
    name = "clang_tidy_fail",
    tags = [
        "manual",
    ],
    targets = [
        "test_pass",
        "test_fail",
    ],
)

# This simple clang -analyze test should pass
clang_analyze_test(
    name = "clang_analyze_pass",
    options = [
        "-fno-color-diagnostics",  # Example
        # "-Xanalyzer -analyzer-disable-all-checks",
    ],
    targets = [
        "test_pass",
    ],
)

# And this clang -analyze test should fail
# Note "manual" tag (means should not be run with other tests)
clang_analyze_test(
    name = "clang_analyze_fail",
    tags = [
        "manual",
    ],
    targets = [
        "test_pass",
        "test_fail",
    ],
)

# This simple clang -analyze + CTU test should pass
clang_ctu_test(
    name = "clang_ctu_pass",
    targets = [
        "test_pass",
    ],
)

# And this clang -analyze + CTU test should fail
# Note "manual" tag (means should not be run with other tests)
clang_ctu_test(
    name = "clang_ctu_fail",
    options = [
        # "-fno-color-diagnostics",  # Example
        # "-Xanalyzer -analyzer-disable-all-checks",
    ],
    tags = [
        "manual",
    ],
    targets = [
        "test_pass",
        "test_fail",
    ],
)

code_checker_test(
    name = "code_checker_pass",
    options = [
        "--ctu",
    ],
    targets = [
        "test_pass",
    ],
)

code_checker_test(
    name = "code_checker_fail",
    tags = [
        "manual",
    ],
    targets = [
        "test_pass",
        "test_fail",
    ],
)

# FIXME: The following test does not detect CTU problem
# CodeChecker analyze --file --ctu does not work
code_checker_test(
    name = "code_checker_ctu",
    options = [
        "--ctu",
    ],
    tags = [
        "manual",
    ],
    targets = [
        "test_pass",
        "test_fail",
    ],
)
