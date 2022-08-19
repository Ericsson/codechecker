# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Check static analyzer and features on the host machine.
"""


import errno
import re
import subprocess
import tempfile

from codechecker_common.logger import get_logger

LOG = get_logger('analyzer')


def check_analyzer(compiler_bin, env):
    """
    Simple check if clang is available.
    """
    clang_version_cmd = [compiler_bin, '--version']
    LOG.debug_analyzer(' '.join(clang_version_cmd))
    try:
        res = subprocess.call(
            clang_version_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        if not res:
            return True

        LOG.debug_analyzer('Failed to run: "%s"', ' '.join(clang_version_cmd))
        return False

    except OSError as oerr:
        if oerr.errno == errno.ENOENT:
            LOG.error(oerr)
            LOG.error('Failed to run: "%s"', ' '.join(clang_version_cmd))
            return False


def has_analyzer_config_option(clang_bin, config_option_name, env=None):
    """Check if an analyzer config option is available."""
    cmd = [clang_bin, "-cc1", "-analyzer-config-help"]

    LOG.debug('run: "%s"', ' '.join(cmd))

    try:
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=env, encoding="utf-8", errors="ignore")
        out, err = proc.communicate()
        LOG.debug("stdout:\n%s", out)
        LOG.debug("stderr:\n%s", err)

        match = re.search(config_option_name, out)
        if match:
            LOG.debug("Config option '%s' is available.", config_option_name)
        return (True if match else False)

    except OSError:
        LOG.error('Failed to run: "%s"', ' '.join(cmd))
        raise


def has_analyzer_option(clang_bin, feature, env=None):
    """Test if the analyzer has a specific option.

    Testing a feature is done by compiling a dummy file."""
    with tempfile.NamedTemporaryFile("w", encoding='utf-8') as inputFile:
        inputFile.write("void foo(){}")
        inputFile.flush()
        cmd = [clang_bin, "-x", "c", "--analyze"]
        cmd.extend(feature)
        cmd.extend([inputFile.name, "-o", "-"])

        LOG.debug('run: "%s"', ' '.join(cmd))
        try:
            proc = subprocess.Popen(cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    env=env, encoding="utf-8", errors="ignore")
            out, err = proc.communicate()
            LOG.debug("stdout:\n%s", out)
            LOG.debug("stderr:\n%s", err)

            return proc.returncode == 0
        except OSError:
            LOG.error('Failed to run: "%s"', ' '.join(cmd))
            return False
