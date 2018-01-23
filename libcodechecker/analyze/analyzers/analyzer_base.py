# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from abc import ABCMeta, abstractmethod
import os
import shlex
import signal
import subprocess
import sys

from libcodechecker.logger import get_logger

LOG = get_logger('analyzer')


class SourceAnalyzer(object):
    """
    Base class for different source analyzers.
    """
    __metaclass__ = ABCMeta

    def __init__(self, config_handler, buildaction):
        self.__config_handler = config_handler
        self.__build_action = buildaction
        self.__source_file = ''
        self.__checkers = []

    @property
    def checkers(self):
        return self.__checkers

    @property
    def buildaction(self):
        return self.__build_action

    @property
    def config_handler(self):
        return self.__config_handler

    @property
    def source_file(self):
        """
        The currently analyzed source file.
        """
        return self.__source_file

    @source_file.setter
    def source_file(self, file_path):
        """
        The currently analyzed source file.
        """
        self.__source_file = file_path

    @abstractmethod
    def construct_analyzer_cmd(self, result_handler):
        """
        Construct the analyzer command.
        """
        pass

    @classmethod
    def resolve_missing_binary(cls, configured_binary, env):
        """
        In case of the configured binary for the analyzer is not found in the
        PATH, this method is used to find a callable binary.
        """
        pass

    @abstractmethod
    def get_analyzer_mentioned_files(self, output):
        """
        Return a collection of files that were mentioned by the analyzer in
        its standard outputs, which should be analyzer_stdout or
        analyzer_stderr from a result handler.
        """
        pass

    def analyze(self, res_handler, env=None, proc_callback=None):
        """
        Run the analyzer.
        """
        LOG.debug('Running analyzer ...')

        # NOTICE!
        # The currently analyzed source file needs to be set before the
        # analyzer command is constructed.
        # The analyzer output file is based on the currently analyzed source.
        res_handler.analyzed_source_file = self.source_file

        # Construct the analyzer cmd.
        analyzer_cmd = self.construct_analyzer_cmd(res_handler)

        LOG.debug_analyzer('\n' + ' '.join(analyzer_cmd))

        res_handler.analyzer_cmd = analyzer_cmd
        analyzer_cmd = ' '.join(analyzer_cmd)
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

    @abstractmethod
    def get_analyzer_checkers(self, config_handler, env):
        """
        Return the checkers available in the analyzer.
        """
        pass

    @staticmethod
    def run_proc(command, env=None, cwd=None, proc_callback=None):
        """
        Just run the given command and return the return code
        and the stdout and stderr outputs of the process.
        """

        def signal_handler(*args, **kwargs):
            # Clang does not kill its child processes, so I have to.
            try:
                g_pid = proc.pid
                os.killpg(g_pid, signal.SIGTERM)
            finally:
                sys.exit(os.EX_OK)

        signal.signal(signal.SIGINT, signal_handler)
        cmd = shlex.split(command)

        proc = subprocess.Popen(cmd,
                                bufsize=-1,
                                env=env,
                                preexec_fn=os.setsid,
                                cwd=cwd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        # Send the created analyzer process' object if somebody wanted it.
        if proc_callback:
            proc_callback(proc)

        stdout, stderr = proc.communicate()
        return proc.returncode, stdout, stderr
