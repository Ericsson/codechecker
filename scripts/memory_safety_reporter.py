#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Memory Safety Report Generator"""


import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def generate_checker_details(to_dir: Path):
    """Generate checker_details.json file using `CodeChecker checkers`"""
    with subprocess.Popen(
        [
            "CodeChecker",
            "checkers",
            "--guideline",
            "memory-safety",
            "-o",
            "json",
            "--details"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    ) as process:
        while process.poll() is None:
            pass
        if process.returncode != 0:
            raise RuntimeError("Failed to get checker details")
        out, _ = process.communicate()
        with open(os.path.join(to_dir, "checker_details.json"), "wb") as file:
            file.write(out)


def generate_reports_sarif(reports_dir: Path, to_dir: Path):
    """Generate reports.sarif file using the reports directory"""
    result = subprocess.run(
        [
            "CodeChecker",
            "parse",
            reports_dir,
            "-e",
            "sarif",
            "-o",
            os.path.join(to_dir, "reports.sarif")
        ],
        check=False
    )

    if result.returncode not in (2, 0):
        raise RuntimeError("Failed to parse reports directory")


def collect_argsfiles(reports_dir: Path, to_dir: Path):
    """Collect all args files (e.g. saargs, tidyargs)"""
    shutil.copytree(os.path.join(reports_dir, "conf"), to_dir)


def generate_checksum(path: Path):
    """Generate checksum file recursively for all files
    originated from `path`"""
    checksum_file = os.path.join(path, "CHECKSUMS.sha256")
    with open(checksum_file, "w", encoding="utf-8") as file:
        for root, _, files in os.walk(path):
            for filename in files:
                if filename == "CHECKSUMS.sha256":
                    continue
                filepath = os.path.join(root, filename)
                sha256 = hashlib.sha256()
                with open(filepath, "rb") as file_handle:
                    for chunk in iter(
                        lambda fh=file_handle: fh.read(8192), b""
                    ):
                        sha256.update(chunk)
                rel_path = os.path.relpath(filepath, path)
                file.write(f"{sha256.hexdigest()}\t{rel_path}\n")


def create_package(parsed_args):
    """Assemble and generate package"""
    set_arguments = [parsed_args.output_file]
    for arg_val in [
        parsed_args.product_name,
        parsed_args.revision,
        parsed_args.binary_name,
        parsed_args.build_id,
        parsed_args.timestamp
    ]:
        if arg_val is not None:
            set_arguments.append(arg_val)
    base_file_name = "_".join(set_arguments)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        base_dir = temp_dir / base_file_name
        base_dir.mkdir(parents=True, exist_ok=True)

        generate_reports_sarif(parsed_args.report_directory, base_dir)

        shutil.copy(
            os.path.join(parsed_args.report_directory, "metadata.json"),
            base_dir
        )

        generate_checker_details(base_dir)

        config_dir = base_dir / "config"
        collect_argsfiles(parsed_args.report_directory, config_dir)

        generate_checksum(base_dir)

        print("Creating package with name: ", base_file_name)
        shutil.make_archive(
            base_name=base_file_name,
            format=parsed_args.extension,
            root_dir=temp_dir,
            base_dir=base_file_name
        )


if __name__ == '__main__':
    DESCRIPTION = '''Memory safety analysis report creator tool.'''

    parser = argparse.ArgumentParser(
        description=DESCRIPTION)

    parser.add_argument('-o',
                        type=str,
                        dest="output_file",
                        required=False,
                        help="The name of the output archive",
                        default="memory_safety_report")
    parser.add_argument('-r',
                        type=str,
                        dest="report_directory",
                        required=True,
                        help="The path of the report directory")
    parser.add_argument('-p',
                        type=str,
                        dest="product_name",
                        required=False,
                        help="Product or system identifier (e.g. CXC123456)")
    parser.add_argument('-v',
                        type=str,
                        dest="revision",
                        required=False,
                        help="RState of the product (e.g. R10S25)")
    parser.add_argument('-b',
                        type=str,
                        dest="binary_name",
                        required=False,
                        help="Name of the binary (e.g. tinyxml)")
    parser.add_argument('-d',
                        type=str,
                        dest="build_id",
                        required=False,
                        help="""Build or pipeline identifier (e.g. CI job id,
                                LMC, branch+change, commit hash)""")
    parser.add_argument('-t',
                        type=str,
                        dest="timestamp",
                        required=False,
                        help="Timestamp at the end of the analysis, in UTC")
    parser.add_argument('-x',
                        choices=['gztar', 'zip'],
                        type=str,
                        dest="extension",
                        required=False,
                        help="The extension of the archive (e.g. tar.gz, zip)")

    args = parser.parse_args()

    create_package(args)
