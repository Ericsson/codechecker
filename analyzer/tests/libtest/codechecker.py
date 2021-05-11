# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helper commands to run CodeChecker in the tests easier.
"""


import os
import shlex
import subprocess

from . import project


def call_command(cmd, cwd, env):
    """
    Execute a process in a test case.  If the run is successful do not bloat
    the test output, but in case of any failure dump stdout and stderr.
    Returns (stdout, stderr) pair of strings.
    """
    def show(out, err):
        print("\nTEST execute stdout:\n")
        print(out)
        print("\nTEST execute stderr:\n")
        print(err)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        if proc.returncode != 0:
            show(out, err)
            print('Unsuccessful run: "' + ' '.join(cmd) + '"')
            print(proc.returncode)
        return out, err, proc.returncode
    except OSError as oerr:
        print(oerr)
        show(out, err)
        print('Failed to run: "' + ' '.join(cmd) + '"')
        raise


def log_and_analyze(codechecker_cfg, test_project_path, clean_project=True):
    """
    Analyze a test project.

    :checkers parameter should be a list of enabled or disabled checkers
    Example: ['-d', 'deadcode.DeadStores']

    """

    build_cmd = project.get_build_cmd(test_project_path)
    build_json = os.path.join(codechecker_cfg['workspace'], "build.json")

    if clean_project:
        ret = project.clean(test_project_path)
        if ret:
            return ret

    log_cmd = ['CodeChecker', 'log',
               '-o', build_json,
               '-b', "'" + build_cmd + "'",
               ]

    analyze_cmd = ['CodeChecker', 'analyze',
                   build_json,
                   '-o', codechecker_cfg['reportdir']]

    suppress_file = codechecker_cfg.get('suppress_file')
    if suppress_file:
        analyze_cmd.extend(['--suppress', suppress_file])

    skip_file = codechecker_cfg.get('skip_file')
    if skip_file:
        analyze_cmd.extend(['--skip', skip_file])

    analyze_cmd.extend(codechecker_cfg['checkers'])
    try:
        print("LOG: " + ' '.join(log_cmd))
        proc = subprocess.Popen(
            shlex.split(
                ' '.join(log_cmd)),
            cwd=test_project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        print(out)
        print(err)

        print("ANALYZE:")
        print(shlex.split(' '.join(analyze_cmd)))
        proc = subprocess.Popen(
            shlex.split(
                ' '.join(analyze_cmd)),
            cwd=test_project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        print(out)
        print(err)
        return 0
    except subprocess.CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode
