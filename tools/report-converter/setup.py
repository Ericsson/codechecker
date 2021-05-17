#!/usr/bin/env python3

import os
import setuptools
import codechecker_report_converter

readme_file_path = os.path.join(
    "..", "..", "docs", "tools", "report-converter.md")

with open(readme_file_path, "r", encoding="utf-8", errors="ignore") as fh:
    long_description = fh.read()

setuptools.setup(
    name=codechecker_report_converter.__title__,
    version=codechecker_report_converter.__version__,
    author='CodeChecker Team (Ericsson)',
    description="Parse and create HTML files from one or more '.plist' "
                "result files.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ericsson/CodeChecker",
    keywords=['report-converter', 'codechecker', 'plist'],
    license='LICENSE.txt',
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=[
        "codechecker_report_hash"
    ],
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3"
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'report-converter = codechecker_report_converter.cli:main'
        ]
    },
)
