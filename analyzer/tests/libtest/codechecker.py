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

from distutils import util
from typing import Dict

from codechecker_analyzer import host_check

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

    cmd_log = ' '.join([shlex.quote(x) for x in cmd])
    try:
        # In case the Popen fails, have these initialized.
        out = ''
        err = ''
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
            print(f'Unsuccessful run: {cmd_log}')
            print(proc.returncode)
        return out, err, proc.returncode
    except OSError as oerr:
        print(oerr)
        show(out, err)
        print(f'Failed to run: {cmd_log}')
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


def check_force_ctu_capable(is_capable):
    """
    Returns True if the given parameter is True or if CTU is force enabled by
    the 'CC_TEST_FORCE_CTU_CAPABLE' environment variable.
    """
    if not is_capable:
        try:
            return bool(util.strtobool(
                os.environ['CC_TEST_FORCE_CTU_CAPABLE']))
        except (ValueError, KeyError):
            pass

    return is_capable


def check_force_extdef_mapping_can_read_pch():
    """
    Returns True if extdef mapping is force enabled by the
    'CC_TEST_FORCE_EXTDEF_MAPPING_CAN_READ_PCH' environment variable.
    """
    try:
        return bool(util.strtobool(
            os.environ['CC_TEST_FORCE_EXTDEF_MAPPING_CAN_READ_PCH']))
    except (ValueError, KeyError):
        pass

    return False


def is_ctu_capable(output: str) -> bool:
    """
    Returns True if the used clang is CTU capable or if it's force enabled by
    environment variable.
    """
    return check_force_ctu_capable('--ctu' in output)


def is_ctu_on_demand_capable(output: str) -> bool:
    """
    Returns True if the used clang is CTU on demand capable or if it's force
    enabled by environment variable.
    """
    return check_force_ctu_capable('--ctu-ast-mode' in output)


def is_ctu_display_progress_capable(
    clangsa_path: str,
    env: Dict
) -> bool:
    """
    Returns True if the used clang is CTU display progress capable or if it's
    force enabled by environment variable.
    """
    ctu_display_progress_capable = host_check.has_analyzer_config_option(
        clangsa_path, 'display-ctu-progress', env)

    return check_force_ctu_capable(ctu_display_progress_capable)
