# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import sys
import signal
import subprocess

from abc import ABCMeta, abstractmethod

from codechecker_lib import logger

LOG = logger.get_new_logger('ANALYZER_BASE')


class SourceAnalyzer(object):
    """
    base class for different source analyzers
    """
    __metaclass__ = ABCMeta

    def __init__(self, config_handler, buildaction):
        self.__config_handler = config_handler
        self.__buildaction = buildaction
        self.__source_file = ''

    @property
    def buildaction(self):
        return self.__buildaction

    @property
    def config_handler(self):
        return self.__config_handler

    @property
    def source_file(self):
        """
        the currently analyzed source file
        """
        return self.__source_file

    @source_file.setter
    def source_file(self, file_path):
        """
        the currently analyzed source file
        """
        self.__source_file = file_path

    @abstractmethod
    def construct_analyzer_cmd(self):
        """
        construct the analyzer command
        """
        pass

    def analyze(self, res_handler, env=None):
        """
        run the analyzer
        """
        LOG.debug('Running analyzer ...')

        def signal_handler(*args, **kwargs):
            # Clang does not kill its child processes, so I have to
            try:
                g_pid = result.pid
                os.killpg(g_pid, signal.SIGTERM)
            finally:
                sys.exit(os.EX_OK)

        signal.signal(signal.SIGINT, signal_handler)

        # NOTICE!
        # the currently analyzed source file needs to be set beforer the
        # analyzer command is constructed
        # the analyzer output file is based on the currently analyzed source
        res_handler.analyzed_source_file = self.source_file

        # construct the analyzer cmd
        analyzer_cmd = self.construct_analyzer_cmd(res_handler)

        LOG.debug(' '.join(analyzer_cmd))

        res_handler.analyzer_cmd = analyzer_cmd

        try:
            proc = subprocess.Popen(analyzer_cmd,
                                    bufsize=-1,
                                    env=env,
                                    preexec_fn=os.setsid,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

            (stdout, stderr) = proc.communicate()

            res_handler.analyzer_returncode = proc.returncode
            res_handler.analyzer_stdout = stdout
            res_handler.analyzer_stderr = stderr
            return res_handler

        except Exception as ex:
            LOG.error(ex)
            res_handler.analyzer_returncode = 1
            return res_handler

    @abstractmethod
    def get_analyzer_checkers(self):
        """
        return the checkers available in the analyzer
        """
        pass
