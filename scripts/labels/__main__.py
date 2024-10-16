#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Dispatching to the top-level tools implemented in the package."""
import argparse
import sys


try:
    from .doc_url.generate_tool import __main__ as doc_url_generate
    from .doc_url.verify_tool import __main__ as doc_url_verify
    from .invariant_check.tool import __main__ as invariant_check
    from .severity.generate_tool import __main__ as severity_generate
except ModuleNotFoundError as e:
    import traceback
    traceback.print_exc()

    print("\nFATAL: Failed to import some required modules! "
          "Please make sure you also install the contents of the "
          "'requirements.txt' of this tool into your virtualenv:\n"
          "\tpip install -r scripts/requirements.txt",
          file=sys.stderr)
    sys.exit(1)


def args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=__package__,
        description="""
Tooling related to creating, managing, verifying, and updating the checker
labels in a CodeChecker config directory.
This main script is the union of several independent tools using a common
internal library.
""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(
        title="subcommands",
        description="""
'label-tool' is a collection of semi-individual sub-tools.
Please select one to continue.
""",
        dest="subcommand",
        required=True)

    def add_subparser(package):
        subparser = subparsers.add_parser(
            list(globals().keys())[list(globals().values()).index(package)],
            prog=package.__package__,
            help=package.short_help,
            description=package.description,
            epilog=package.epilogue,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        subparser = package.arg_parser(subparser)
        subparser.set_defaults(__main=package.main)

    add_subparser(doc_url_generate)
    add_subparser(doc_url_verify)
    add_subparser(invariant_check)
    add_subparser(severity_generate)

    return parser


if __name__ == "__main__":
    def _main():
        _args = args().parse_args()
        del _args.__dict__["subcommand"]

        main = _args.__dict__["__main"]
        del _args.__dict__["__main"]

        sys.exit(main(_args) or 0)
    _main()
