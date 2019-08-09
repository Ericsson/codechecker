# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Test project helpers.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

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
        json.load(open(test_proj_cfg))
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
        proc = subprocess.Popen(shlex.split(clean_cmd),
                                cwd=project_path,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=environment)
        _, _ = proc.communicate()
        return 0
    except subprocess.CalledProcessError as cerr:
        return cerr.returncode
