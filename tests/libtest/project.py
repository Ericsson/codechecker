# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
import os
import json
import shlex
import subprocess
from . import env


def get_info(proj_path):
    test_proj_cfg = os.path.join(os.path.realpath(proj_path),
                                 'project_info.json')
    project_info = \
        json.load(open(test_proj_cfg))
    return project_info


def path():
    proj_path = os.environ.get('TEST_PROJ')
    if not proj_path:
        proj_path = os.path.join(env.repository_root,
                                 'tests',
                                 'projects',
                                 'cpp')
    return proj_path


def get_build_cmd(project_path):
    return get_info(project_path)['build_cmd']


def get_clean_cmd(project_path):
    return get_info(project_path)['clean_cmd']


def clean(test_project_path, env=None):
    """Clean the test project."""

    clean_cmd = get_clean_cmd(test_project_path)
    print(clean_cmd)
    command = ['bash', '-c']
    command.extend(shlex.split(clean_cmd))
    print(test_project_path)
    try:
        print(command)
        proc = subprocess.Popen(command,
                                cwd=test_project_path,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=env)
        out, err = proc.communicate()
        print(out)
        print(err)
        return 0
    except subprocess.CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode
