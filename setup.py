#!/usr/bin/env python3

import json
import os
import re
import shutil
import subprocess
import time
import warnings

import setuptools
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PREFIX = os.path.join("share", "codechecker")
CONFIG_DIR = os.path.join(ROOT, "config")

PACKAGE_DIR = {
    "codechecker_common": "codechecker_common",
    "codechecker_analyzer": "analyzer/codechecker_analyzer",
    "codechecker_merge_clang_extdef_mappings":
        "analyzer/tools/merge_clang_extdef_mappings"
    "/codechecker_merge_clang_extdef_mappings",
    "codechecker_statistics_collector": "analyzer/tools/statistics_collector"
    "/codechecker_statistics_collector",
    "codechecker_report_converter":
        "tools/report-converter/codechecker_report_converter",
    "tu_collector": "tools/tu_collector/tu_collector",
    "codechecker_web": "web/codechecker_web",
    "codechecker_client": "web/client/codechecker_client",
    "codechecker_server": "web/server/codechecker_server",
}

CONFIG_EXTRA_ROOTS = [
    os.path.join("analyzer", "config"),
    os.path.join("web", "config"),
    os.path.join("web", "server", "config"),
]

VERSION_SOURCES = [
    os.path.join("analyzer", "config", "analyzer_version.json"),
    os.path.join("web", "config", "web_version.json"),
]

PACKAGE_DATA = {
    "codechecker_report_converter": [
        "report/output/html/static/**/*",
        "report/output/html/static/*",
    ],
}


def find_all_packages():
    pkgs = []
    for top_pkg, src_dir in PACKAGE_DIR.items():
        pkgs.append(top_pkg)
        abs_src = os.path.join(ROOT, src_dir)
        for sub in setuptools.find_packages(where=abs_src):
            pkgs.append(f"{top_pkg}.{sub}")
    return pkgs


def build_package_dir():
    mapping = {}
    for top_pkg, src_dir in PACKAGE_DIR.items():
        mapping[top_pkg] = src_dir
        abs_src = os.path.join(ROOT, src_dir)
        for sub in setuptools.find_packages(where=abs_src):
            mapping[f"{top_pkg}.{sub}"] = os.path.join(
                src_dir, sub.replace(".", os.sep)
            )
    return mapping


def add_git_info(data):
    if not os.path.exists(os.path.join(ROOT, ".git")):
        return
    try:
        data["git_hash"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            encoding="utf-8",
            errors="ignore",
        ).strip()
    except (subprocess.CalledProcessError, OSError):
        return

    version = data.get("version", {})
    ver_str = "{}.{}.{}".format(
        version.get("major", "0"),
        version.get("minor", "0"),
        version.get("revision", "0"),
    )
    rc = version.get("rc", "")
    if rc:
        ver_str += f"-rc{rc}"

    try:
        tag = subprocess.check_output(
            ["git", "describe", "--always", "--tags", "--abbrev=0"],
            cwd=ROOT,
            encoding="utf-8",
            errors="ignore",
        ).strip()
        dirty = subprocess.check_output(
            ["git", "describe", "--always", "--tags", "--dirty=-tainted"],
            cwd=ROOT,
            encoding="utf-8",
            errors="ignore",
        ).strip()
        data["git_describe"] = {
            "tag": ver_str,
            "dirty": dirty.replace(tag, ver_str),
        }
    except (subprocess.CalledProcessError, OSError):
        pass


def merge_config():
    version_basenames = {os.path.basename(v) for v in VERSION_SOURCES}
    for config_root in CONFIG_EXTRA_ROOTS:
        abs_root = os.path.join(ROOT, config_root)
        if not os.path.isdir(abs_root):
            continue
        for name in os.listdir(abs_root):
            src = os.path.join(abs_root, name)
            dest = os.path.join(CONFIG_DIR, name)
            if name in version_basenames:
                continue  # handled below with git extension
            if os.path.isfile(src) and not os.path.exists(dest):
                shutil.copy2(src, dest)

    for vf in VERSION_SOURCES:
        src = os.path.join(ROOT, vf)
        if not os.path.isfile(src):
            continue
        with open(src) as f:
            data = json.load(f)
        data["package_build_date"] = time.strftime("%Y-%m-%dT%H:%M")
        add_git_info(data)
        dest = os.path.join(CONFIG_DIR, os.path.basename(vf))
        with open(dest, "w") as f:
            json.dump(data, f, sort_keys=True, indent=4)


def collect_data_files():
    files = []

    files.append(
        (
            os.path.join(DATA_PREFIX, "docs"),
            [os.path.join("docs", "README.md")],
        )
    )

    for req in [
        os.path.join("analyzer", "requirements.txt"),
        os.path.join("web", "requirements.txt"),
    ]:
        files.append((os.path.join(DATA_PREFIX, os.path.dirname(req)), [req]))

    for dirpath, _, filenames in os.walk(CONFIG_DIR):
        if not filenames:
            continue
        rel = os.path.relpath(dirpath, CONFIG_DIR)
        dest = os.path.join(DATA_PREFIX, "config")
        if rel != ".":
            dest = os.path.join(dest, rel)
        files.append(
            (
                os.path.normpath(dest),
                [
                    os.path.join(
                        "config",
                        os.path.relpath(os.path.join(dirpath, f), CONFIG_DIR),
                    )
                    for f in filenames
                ],
            )
        )

    return files


def get_requirements():
    req_files = [
        os.path.join("analyzer", "requirements.txt"),
        os.path.join("web", "requirements.txt"),
    ]
    seen = {}  # normalised name -> (specifier, source file)
    reqs = []
    for path in req_files:
        with open(os.path.join(ROOT, path)) as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if not line or "codechecker" in line:
                    continue
                name = re.split(r"[~!=<>]", line, 1)[0].strip().lower()
                if name in seen:
                    prev_spec, prev_file = seen[name]
                    if prev_spec != line:
                        warnings.warn(
                            f"Requirement {name!r} differs: "
                            f"{prev_spec!r} (from {prev_file}) vs "
                            f"{line!r} (from {path})"
                        )
                    continue
                seen[name] = (line, path)
                reqs.append(line)
    return reqs


def read_long_description():
    with open(
        os.path.join(ROOT, "docs", "README.md"),
        encoding="utf-8",
        errors="ignore",
    ) as fh:
        return fh.read()


class BuildPyWithConfig(build_py):
    def run(self):
        merge_config()
        self.distribution.data_files = collect_data_files()
        super().run()


class SdistWithConfig(sdist):
    def run(self):
        merge_config()
        self.distribution.data_files = collect_data_files()
        super().run()


setuptools.setup(
    name="codechecker",
    version="6.29.0",
    author='CodeChecker Team (Ericsson)',
    author_email='codechecker-tool@googlegroups.com',
    description="CodeChecker is an analyzer tooling, defect database and "
                "viewer extension",
    long_description=read_long_description(),
    long_description_content_type = "text/markdown",
    url="https://github.com/Ericsson/CodeChecker",
    project_urls={
        "Documentation": "http://codechecker.readthedocs.io",
        "Issue Tracker": "http://github.com/Ericsson/CodeChecker/issues",
    },
    keywords=["codechecker", "plist", "sarif"],
    license="Apache-2.0 WITH LLVM-exception",
    packages=find_all_packages(),
    package_dir=build_package_dir(),
    package_data=PACKAGE_DATA,
    # data_files are collected inside the build hooks (see
    # BuildPyWithConfig) because merge_config() must create the
    # version JSON files before collect_data_files() walks config/.
    data_files=[],
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Bug Tracking",
        "Topic :: Software Development :: Quality Assurance",
    ],
    install_requires=get_requirements(),
    cmdclass={
        "build_py": BuildPyWithConfig,
        "sdist": SdistWithConfig,
    },
    python_requires=">=3.9",
    scripts=["scripts/gerrit_changed_files_to_skipfile.py"],
    entry_points={
        "console_scripts": [
            "CodeChecker = codechecker_common.cli:main",
            "merge-clang-extdef-mappings = "
            "codechecker_merge_clang_extdef_mappings.cli:main",
            "post-process-stats = codechecker_statistics_collector.cli:main",
            "report-converter = codechecker_report_converter.cli:main",
            "tu_collector = tu_collector.tu_collector:main",
        ],
    },
)
