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


def get_info(test_project):
    test_proj_cfg = os.path.join(os.path.realpath(path(test_project)),
                                 'project_info.json')
    project_info = \
        json.load(open(test_proj_cfg))
    return project_info


def path(test_project):
    return os.path.join(env.repository_root(),
                        'tests',
                        'projects',
                        test_project)


def get_build_cmd(test_project):
    return get_info(test_project)['build_cmd']


def get_clean_cmd(test_project):
    return get_info(test_project)['clean_cmd']


def clean(test_project, env=None):
    """Clean the test project."""

    project_path = path(test_project)
    clean_cmd = get_clean_cmd(project_path)
    print(clean_cmd)
    command = ['bash', '-c']
    command.extend(shlex.split(clean_cmd))
    print(project_path)
    try:
        print(command)
        proc = subprocess.Popen(command,
                                cwd=project_path,
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
