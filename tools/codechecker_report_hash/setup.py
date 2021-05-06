#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import setuptools

readme_file_path = os.path.join(
    "..", "..", "docs", "tools", "codechecker_report_hash.md")

with open(readme_file_path, "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="codechecker_report_hash",
    version="0.1.0",
    author='CodeChecker Team (Ericsson)',
    description="Module to generate report hash for CodeChecker.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ericsson/CodeChecker",
    keywords=['plist', 'report', 'hash'],
    license='LICENSE.txt',
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
    ]
)
