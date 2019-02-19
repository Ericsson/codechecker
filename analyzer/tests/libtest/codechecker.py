# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Helper commands to run CodeChecker in the tests easier.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import subprocess


def call_command(cmd, cwd, env):
    """
    Execute a process in a test case.  If the run is successful do not bloat
    the test output, but in case of any failure dump stdout and stderr.
    Returns the utf decoded (stdout, stderr) pair of strings.
    """
    def show(out, err):
        print("\nTEST execute stdout:\n")
        print(out.decode("utf-8"))
        print("\nTEST execute stderr:\n")
        print(err.decode("utf-8"))
    try:
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=cwd, env=env)
        out, err = proc.communicate()
        if proc.returncode != 0:
            show(out, err)
            print('Unsuccessful run: "' + ' '.join(cmd) + '"')
            raise Exception("Unsuccessful run of command.")
        return out.decode("utf-8"), err.decode("utf-8")
    except OSError:
        show(out, err)
        print('Failed to run: "' + ' '.join(cmd) + '"')
        raise
