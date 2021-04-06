# cc_binary for simple test_main
load(
    "@rules_cc//cc:defs.bzl",
    "cc_binary",
    "cc_library",
)

# Test for strip_include_prefix
cc_library(
    name = "inc",
    hdrs = glob(["inc/*.h"]),
    strip_include_prefix = "inc",
)

# Simplest C++ test
cc_binary(
    name = "main",
    srcs = ["main.cc"],
    deps = ["inc"],
)
