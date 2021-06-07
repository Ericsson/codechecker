#!/usr/bin/env python3

import os
import setuptools
import subprocess
import sys

from setuptools.command.build_ext import build_ext
from setuptools.command.install import install
from setuptools.command.sdist import sdist
from setuptools.extension import Extension

curr_dir = os.path.dirname(os.path.realpath(__file__))
build_dir = os.path.join(curr_dir, "build_dist")
package_dir = os.path.join("build_dist", "CodeChecker")
lib_dir = os.path.join(package_dir, "lib", "python3")
req_file_paths = [
    os.path.join("analyzer", "requirements.txt"),
    os.path.join("web", "requirements.txt")]
data_files_dir_path = os.path.join('share', 'codechecker')

data_files = [
    (os.path.join(data_files_dir_path, "docs"), [
        os.path.join("docs", "README.md")]),

    *[(os.path.join(data_files_dir_path, os.path.dirname(p)), [p])
      for p in req_file_paths]
]

packages = []


def get_requirements():
    """ Get install requirements. """
    requirements = set()
    for req_file_path in req_file_paths:
        with open(req_file_path, 'r') as f:
            requirements.update([s for s in [
                line.split('#', 1)[0].strip(' \t\n') for line in f]
                if s and 'codechecker' not in s])

    return requirements


def init_data_files():
    """ Initalize data files which will be copied into the package. """
    for data_dir_name in ['config', 'www']:
        data_dir_path = os.path.join(package_dir, data_dir_name)
        for root, _, files in os.walk(data_dir_path):
            if not files:
                continue

            data_files.append((
                os.path.normpath(
                        os.path.join(data_files_dir_path, data_dir_name,
                                    os.path.relpath(root, data_dir_path))),
                [os.path.join(root, file_path) for file_path in files]))


def init_packages():
    """ Find and initialize the list of packages. """
    global packages
    packages.extend(setuptools.find_packages(where=lib_dir))


ld_logger_src_dir_path = \
    os.path.join("analyzer", "tools", "build-logger", "src")

ld_logger_sources = [
    'ldlogger-hooks.c',
    'ldlogger-logger.c',
    'ldlogger-tool.c',
    'ldlogger-tool-gcc.c',
    'ldlogger-tool-javac.c',
    'ldlogger-util.c'
]

ld_logger_includes = [
    'ldlogger-hooks.h',
    'ldlogger-tool.h',
    'ldlogger-util.h'
]

data_files.append(
    (
        os.path.join(data_files_dir_path, 'ld_logger', 'include'),
        [os.path.join(ld_logger_src_dir_path, i) for i in ld_logger_includes]
    )
)

module_logger_name = 'codechecker_analyzer.ld_logger.lib.ldlogger'
module_logger = Extension(
    module_logger_name,
    define_macros=[('__LOGGER_MAIN__', None), ('_GNU_SOURCE', None)],
    extra_link_args=[
        '-O2', '-fomit-frame-pointer', '-fvisibility=hidden', '-pedantic',
        '-Wl,--no-as-needed', '-ldl'
    ],
    sources=[
        os.path.join(ld_logger_src_dir_path, s) for s in ld_logger_sources])


class BuildExt(build_ext):
    def get_ext_filename(self, ext_name):
        return f"{os.path.join(*ext_name.split('.'))}.so"

    def build_extension(self, ext):
        if sys.platform == "linux":
            build_ext.build_extension(self, ext)


class Sdist(sdist):
    def run(self):
        res = subprocess.call(
            ["make", "clean_package", "package", "package_api"],
            env=dict(os.environ,
                     BUILD_DIR=build_dir),
            encoding="utf-8",
            errors="ignore")

        if res:
            sys.exit(1)

        init_data_files()
        init_packages()

        return sdist.run(self)


class Install(install):
    def run(self):
        init_data_files()
        init_packages()

        return install.run(self)

with open(os.path.join("docs", "README.md"), "r",
          encoding="utf-8", errors="ignore") as fh:
    long_description = fh.read()


setuptools.setup(
    name="codechecker",
    version="6.17.0",
    author='CodeChecker Team (Ericsson)',
    author_email='csordasmarton92@gmail.com',
    description="CodeChecker is an analyzer tooling, defect database and "
                "viewer extension",
    long_description=long_description,
    long_description_content_type = "text/markdown",
    url="https://github.com/Ericsson/CodeChecker",
    keywords=['codechecker', 'plist'],
    license='LICENSE.TXT',
    packages=packages,
    package_dir={
        "": lib_dir
    },
    data_files=data_files,
    include_package_data=True,
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3"
    ],
    install_requires=list(get_requirements()),
    ext_modules=[module_logger],
    cmdclass={
        'sdist': Sdist,
        'install': Install,
        'build_ext': BuildExt,
    },
    python_requires='>=3.6',
    scripts=[
        'scripts/gerrit_changed_files_to_skipfile.py'
    ],
    entry_points={
        'console_scripts': [
            'CodeChecker = codechecker_common.cli:main',
            'merge-clang-extdef-mappings = codechecker_merge_clang_extdef_mappings.cli:main',
            'post-process-stats = codechecker_statistics_collector.cli:main',
            'report-converter = codechecker_report_converter.cli:main',
            'tu_collector = tu_collector.tu_collector:main'
        ]
    },
)
