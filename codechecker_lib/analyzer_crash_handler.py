# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""Module to handle analyzer crash."""

import shlex
import signal
import subprocess
import tempfile

from codechecker_lib.logger import LoggerFactory


class AnalyzerCrashHandler(object):

    def __init__(self, context, analyzer_env):
        self._context = context
        self._analyzer_env = analyzer_env
        self._logger = LoggerFactory.get_new_logger('ANALYZER_CRASH_HANDLER')

    # -------------------------------------------------------------------------
    def get_crash_info(self, build_cmd):
        """
        Get the crash info by running the build command
        with gdb again if there was some crash.
        """
        def signal_handler(*args, **kwargs):
            try:
                result.terminate()
            finally:
                raise KeyboardInterrupt('CTRL+C')

        signal.signal(signal.SIGINT, signal_handler)

        gdb_cmd = ['gdb', '--batch',
                   '--command=' + self._context.gdb_config_file, '--args']
        gdb_cmd.extend(build_cmd)

        tmp_stdout = tempfile.TemporaryFile()
        tmp_stderr = tempfile.TemporaryFile()
        result = ""

        # Gdb uses python3, so it is crashed when any python2 module in
        # PYTHONPATH.
        # bug: https://bugs.launchpad.net/ubuntu/+source/apport/+bug/1398033
        self._analyzer_env['PYTHONPATH'] = ''

        try:
            result = subprocess.Popen(shlex.split(' '.join(gdb_cmd)),
                                      env=self._analyzer_env,
                                      stdout=tmp_stdout, stderr=tmp_stderr)

            result.wait()

            tmp_stdout.seek(0)
            tmp_stderr.seek(0)

            output_stdout = tmp_stdout.read()
            output_stderr = tmp_stderr.read()
            result = output_stdout + '\n' + output_stderr
        except KeyboardInterrupt:
            raise
        except:
            result = 'Failed to get extra debug information using gdb:\n' + \
                     ' '.join(gdb_cmd)
        finally:
            tmp_stdout.close()
            tmp_stderr.close()

        return result
