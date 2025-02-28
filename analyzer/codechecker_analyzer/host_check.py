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

from codechecker_analyzer import analyzer_context
from codechecker_common.logger import get_logger

LOG = get_logger('analyzer')


def check_analyzer(compiler_bin):
    """
    Simple check if clang is available.
    """
    clang_version_cmd = [compiler_bin, '--version']
    LOG.debug(' '.join(clang_version_cmd))
    environ = analyzer_context.get_context().get_env_for_bin(
        compiler_bin)
    try:
        proc = subprocess.Popen(
            clang_version_cmd,
            env=environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        if not proc.returncode:
            return True
        LOG.error('Failed to run: "%s"', ' '.join(clang_version_cmd))
        LOG.error('stdout: %s', out)
        LOG.error('stderr: %s', err)
        return False

    except OSError as oerr:
        if oerr.errno == errno.ENOENT:
            LOG.error(oerr)
            LOG.error('Failed to run: "%s"', ' '.join(clang_version_cmd))
        return False


def has_analyzer_config_option(clang_bin, config_option_name):
    """Check if an analyzer config option is available."""
    cmd = [clang_bin, "-cc1", "-analyzer-config-help"]

    LOG.debug_analyzer('run: "%s"', ' '.join(cmd))
    context = analyzer_context.get_context()

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=context.get_env_for_bin(clang_bin),
            encoding="utf-8", errors="ignore")
        out, err = proc.communicate()
        LOG.debug_analyzer("stdout:\n%s", out)
        LOG.debug_analyzer("stderr:\n%s", err)

        match = re.search(config_option_name, out)
        if match:
            LOG.debug("Config option '%s' is available.", config_option_name)
        return bool(match)

    except OSError:
        LOG.error('Failed to run: "%s"', ' '.join(cmd))
        raise


def has_analyzer_option(clang_bin, feature):
    """Test if the analyzer has a specific option.

    Testing a feature is done by compiling a dummy file."""
    with tempfile.NamedTemporaryFile("w", encoding='utf-8') as input_file:
        input_file.write("void foo(){}")
        input_file.flush()
        cmd = [clang_bin, "-x", "c", "--analyze"]
        cmd.extend(feature)
        cmd.extend([input_file.name, "-o", "-"])

        LOG.debug_analyzer('run: "%s"', ' '.join(cmd))
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=analyzer_context.get_context().get_env_for_bin(clang_bin),
                encoding="utf-8", errors="ignore")
            out, err = proc.communicate()
            LOG.debug_analyzer("stdout:\n%s", out)
            LOG.debug_analyzer("stderr:\n%s", err)

            return proc.returncode == 0
        except OSError:
            LOG.error('Failed to run: "%s"', ' '.join(cmd))
            return False
