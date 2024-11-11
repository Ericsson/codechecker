#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="statistics-collector",
    version="0.1.0",
    author='CodeChecker Team (Ericsson)',
    description="",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ericsson/CodeChecker",
    keywords=['clang', 'statistics', 'merge', 'static-analysis', 'analysis'],
    license='LICENSE.txt',
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3"
    ],
    entry_points={
        'console_scripts': [
            'post-process-stats = codechecker_statistics_collector.cli:main'
        ]
    },
)
