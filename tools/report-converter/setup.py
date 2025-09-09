#!/usr/bin/env python3

import os
import setuptools
import codechecker_report_converter

# Use a focused description for PyPI while pointing to full documentation
description = """
CodeChecker Report Converter is a Python tool that converts various code analyzer outputs
into CodeChecker format and generates HTML reports. It supports multiple analyzers including:
- Clang-based tools (Clang-Tidy, Sanitizers)
- Static analyzers (Cppcheck, GCC)
- Language-specific linters (ESLint, Pylint, TSLint)

For comprehensive documentation, visit:
https://codechecker.readthedocs.io/en/latest/tools/report-converter/
"""

setuptools.setup(
    name=codechecker_report_converter.__title__,
    version=codechecker_report_converter.__version__,
    author='CodeChecker Team (Ericsson)',
    description="Parse and create HTML files from various code analyzer outputs",
    long_description=description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ericsson/CodeChecker",
    keywords=['report-converter', 'codechecker', 'static-analysis', 'linter'],
    license='LICENSE.txt',
    packages=setuptools.find_namespace_packages(include=['codechecker_report_converter*']),
    include_package_data=True,  # This will use MANIFEST.in
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3"
    ],
    python_requires='>=3.9',
    entry_points={
        'console_scripts': [
            'report-converter = codechecker_report_converter.cli:main',
            'plist-to-html = codechecker_report_converter.report.output.html.cli:main'
        ]
    },
)
