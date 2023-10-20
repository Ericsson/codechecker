# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Base class for various source analyzers.
"""


from abc import ABCMeta, abstractmethod
import os
import signal
import subprocess
import sys
import shlex

from typing import Optional

from codechecker_analyzer import analyzer_context
from codechecker_common.logger import get_logger

LOG = get_logger('analyzer')


def handle_analyzer_executable_from_config(analyzer_name, path):
    context = analyzer_context.get_context()
    if not os.path.isfile(path):
        LOG.error(f"'{path}' is not a path to an analyzer binary "
                  f"given to --analyzer-config={analyzer_name}:executable!")
        sys.exit(1)
    context.analyzer_binaries[analyzer_name] = path


class SourceAnalyzer(metaclass=ABCMeta):
    """
    Base class for different source analyzers.
    """

    def __init__(self, config_handler, buildaction):
        self.__config_handler = config_handler
        self.__build_action = buildaction
        # Currently analyzed source file.
        self.source_file = ''

    @property
    def buildaction(self):
        return self.__build_action

    @property
    def config_handler(self):
        return self.__config_handler

    @abstractmethod
    def construct_analyzer_cmd(self, result_handler):
        raise NotImplementedError("Subclasses should implement this!")

    @classmethod
    def resolve_missing_binary(cls, configured_binary, environ):
        """
        In case of the configured binary for the analyzer is not found in the
        PATH, this method is used to find a callable binary.
        """
        raise NotImplementedError("Subclasses should implement this!")

    @abstractmethod
    def get_binary_version(self, configured_binary, environ, details=False) \
            -> str:
        """
        Return the version number of the binary that CodeChecker found, even
        if its incompatible. If details is true, additional version information
        is provided. If details is false, the return value should be
        convertible to a distutils.version.StrictVersion type.
        """
        raise NotImplementedError("Subclasses should implement this!")

    @classmethod
    def is_binary_version_incompatible(cls, configured_binary, environ) \
            -> Optional[str]:
        """
        CodeChecker can only execute certain versions of analyzers.
        Returns a error object (an optional string). If the return value is
        None, the analyzer binary is compatible with the current CodeChecker
        version. Otherwise, the it should be a message describing the precise
        version mismatch.
        """
        raise NotImplementedError("Subclasses should implement this!")

    @classmethod
    def construct_config_handler(cls, args):
        """ Should return a subclass of AnalyzerConfigHandler."""
        raise NotImplementedError("Subclasses should implement this!")

    @abstractmethod
    def get_analyzer_mentioned_files(self, output):
        """
        Return a collection of files that were mentioned by the analyzer in
        its standard outputs, which should be analyzer_stdout or
        analyzer_stderr from a result handler.
        """
        raise NotImplementedError("Subclasses should implement this!")

    @abstractmethod
    def construct_result_handler(self, buildaction, report_output,
                                 skiplist_handler):
        """
        This method constructs the class that is responsible to handle the
        results of the analysis. The result should be a subclass of
        ResultHandler
        """
        raise NotImplementedError("Subclasses should implement this!")

    def analyze(self, analyzer_cmd, res_handler, proc_callback=None, env=None):
        """
        Run the analyzer.
        """
        LOG.debug('Running analyzer ...')

        LOG.debug_analyzer('\n%s',
                           ' '.join([shlex.quote(x) for x in analyzer_cmd]))

        res_handler.analyzer_cmd = analyzer_cmd
        try:
            ret_code, stdout, stderr \
                = SourceAnalyzer.run_proc(analyzer_cmd,
                                          res_handler.buildaction.directory,
                                          proc_callback,
                                          env)
            res_handler.analyzer_returncode = ret_code
            res_handler.analyzer_stdout = stdout
            res_handler.analyzer_stderr = stderr
            return res_handler

        except Exception as ex:
            LOG.error(ex)
            res_handler.analyzer_returncode = 1
            return res_handler

    @classmethod
    def get_analyzer_checkers(cls):
        """
        Return the checkers available in the analyzer.
        """
        raise NotImplementedError("Subclasses should implement this!")

    def post_analyze(self, result_handler):
        """
        Run immediately after the analyze function.
        """
        pass

    @staticmethod
    def run_proc(command, cwd=None, proc_callback=None, env=None):
        """
        Just run the given command and return the return code
        and the stdout and stderr outputs of the process.
        """

        def signal_handler(signum, frame):
            # Clang does not kill its child processes, so I have to.
            try:
                g_pid = proc.pid
                os.killpg(g_pid, signal.SIGTERM)
            finally:
                sys.exit(128 + signum)

        signal.signal(signal.SIGINT, signal_handler)

        if env is None:
            env = analyzer_context.get_context().analyzer_env

        proc = subprocess.Popen(
            command,
            bufsize=-1,
            env=env,
            preexec_fn=None if sys.platform == 'win32' else os.setsid,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore")

        # Send the created analyzer process' object if somebody wanted it.
        if proc_callback:
            proc_callback(proc)

        stdout, stderr = proc.communicate()
        return proc.returncode, stdout, stderr
