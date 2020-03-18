#!/usr/bin/env python3

import setuptools

with open("README.md", "r", encoding="utf-8", errors="ignore") as fh:
    long_description = fh.read()

setuptools.setup(
    name="compilation database transformer",
    version="0.1.0",
    author='CodeChecker Team (Ericsson)',
    description="Manipulate, preprocess and transform compilation database "
                "JSON files. Provides pretty printing, compilation result "
                "checking and adjusting compilation parameters features.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ericsson/CompilationDatabaseTransformer",
    keywords=['compilation_database_transformer', 'codechecker', 'compilation database', 'compile_commands'],
    license='LICENSE.txt',
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: University of Illinois/NCSA Open Source License",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3"
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'ccdb-tool = compilation_database_transformer.cli:main'
        ]
    },
)
