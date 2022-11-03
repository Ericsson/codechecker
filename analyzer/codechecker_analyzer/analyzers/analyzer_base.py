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

from codechecker_common.logger import get_logger

LOG = get_logger('analyzer')


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

    @classmethod
    def version_compatible(cls, configured_binary, environ):
        """
        CodeChecker can only execute certain versions of analyzers.
        This function should return True if the analyzer binary is
        compatible with the current CodeChecker version.
        """
        raise NotImplementedError("Subclasses should implement this!")

    @classmethod
    def construct_config_handler(cls, args, context):
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
                                 checker_labels, skiplist_handler):
        """
        This method constructs the class that is responsible to handle the
        results of the analysis. The result should be a subclass of
        ResultHandler
        """
        raise NotImplementedError("Subclasses should implement this!")

    def analyze(self, analyzer_cmd, res_handler, env=None, proc_callback=None):
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
                                          env,
                                          res_handler.buildaction.directory,
                                          proc_callback)
            res_handler.analyzer_returncode = ret_code
            res_handler.analyzer_stdout = stdout
            res_handler.analyzer_stderr = stderr
            return res_handler

        except Exception as ex:
            LOG.error(ex)
            res_handler.analyzer_returncode = 1
            return res_handler

    @classmethod
    def get_analyzer_checkers(cls, cfg_handler, environ):
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
    def run_proc(command, env=None, cwd=None, proc_callback=None):
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
