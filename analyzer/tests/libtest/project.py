# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Test project helpers.
"""


import json
import os
import shlex
import subprocess
from . import env


def path(test_project):
    return os.path.join(env.test_proj_root(), test_project)


def get_info(test_project):
    test_proj_cfg = os.path.join(os.path.realpath(path(test_project)),
                                 'project_info.json')
    project_info = \
        json.load(open(test_proj_cfg, encoding="utf-8", errors="ignore"))
    return project_info


def get_build_cmd(test_project):
    return get_info(test_project)['build_cmd']


def get_clean_cmd(test_project):
    try:
        return get_info(test_project)['clean_cmd']
    except KeyError:
        return ""


def clean(test_project, environment=None):
    """Clean the test project."""
    project_path = path(test_project)
    clean_cmd = get_clean_cmd(project_path)
    if not clean_cmd:
        # If the clean command is missing do nothing.
        return 0
    try:
        print(clean_cmd)
        proc = subprocess.Popen(
            shlex.split(clean_cmd),
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            encoding="utf-8",
            errors="ignore")
        _, _ = proc.communicate()
        return 0
    except subprocess.CalledProcessError as cerr:
        return cerr.returncode
