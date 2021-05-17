#!/usr/bin/env python3

import os
import setuptools

readme_file_path = os.path.join(
    "..", "..", "docs", "tools", "tu_collector.md")

with open(readme_file_path, "r", encoding="utf-8", errors="ignore") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tu_collector",
    version="0.1.0",
    author='CodeChecker Team (Ericsson)',
    description="Collect the source files constituting a translation unit.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ericsson/CodeChecker",
    keywords=['tu-collector', 'translation unit', 'collector',
              'compilation database'],
    license='LICENSE.txt',
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'tu-collector = tu_collector.tu_collector:main'
        ]
    },
)
