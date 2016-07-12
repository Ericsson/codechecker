# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import uuid
import ntpath

from abc import ABCMeta, abstractmethod

from codechecker_lib import logger

LOG = logger.get_new_logger('RESULT_HANDLER_BASE')


class ResultHandler(object):
    """
    handle and store the results at runtime for the analyzer
    stdout, stderr, temporarly generated files
    do result postprocessing if required

    For each buildaction there is one result handler
    the result handler can handle multiple results if there
    are more than one analyzed source file in one buildaction

    For each build action
    - postprocess_result and handle_results can be called multiple times
      for the source files in one buildaction they will be analyzed separately
      with the same build options

    Method call order should be this
    postprocess_result()
    handle_results()

    """

    __metaclass__ = ABCMeta
    # handle the output stdout, or plist or both for an analyzer

    def __init__(self, action, workspace):
        """
        put the temporary files for the workspace
        """
        self.__workspace = workspace

        self.__analyzer_cmd = []
        self.__analyzer_stdout = ''
        self.__analyzer_stderr = ''
        self.__severity_map = {}
        self.__skiplist_handler = None
        self.__analyzed_source_file = None
        self.__analyzer_returncode = 1
        self.__buildaction = action

        self.__res_file = None

    @property
    def buildaction(self):
        """
        """
        return self.__buildaction

    @property
    def analyzer_cmd(self):
        """
        set the analyzer cmd
        """
        return self.__analyzer_cmd

    @analyzer_cmd.setter
    def analyzer_cmd(self, cmd):
        """
        set the analyzer cmd
        """
        self.__analyzer_cmd = cmd

    @property
    def result_files(self):
        """
        return the analyzer result files
        """
        return self.__result_files

    @property
    def skiplist_handler(self):
        """
        """
        return self.__skiplist_handler

    @skiplist_handler.setter
    def skiplist_handler(self, handler):
        """
        used to check if analyzer result should be
        handled or just skipped
        """
        self.__skiplist_handler = handler

    @property
    def severity_map(self):
        """
        severity map for each checker
        """
        return self.__severity_map

    @severity_map.setter
    def severity_map(self, value):
        """
        severity map for each checker
        """
        self.__severity_map = value

    @property
    def workspace(self):
        """
        workspace where the analysis results should go
        temporarly generated files
        """
        return self.__workspace

    @property
    def analyzer_returncode(self):
        """
        """
        return self.__analyzer_returncode

    @analyzer_returncode.setter
    def analyzer_returncode(self, return_code):
        """
        """
        self.__analyzer_returncode = return_code

    @property
    def analyzer_stdout(self):
        """
        get the stdout from the analyzer
        """
        return self.__analyzer_stdout

    @analyzer_stdout.setter
    def analyzer_stdout(self, stdout):
        """
        set the stdout of the analyzer
        """
        self.__analyzer_stdout = stdout

    @property
    def analyzer_stderr(self):
        """
        get stderr of the analyzer
        """
        return self.__analyzer_stderr

    @analyzer_stderr.setter
    def analyzer_stderr(self, stderr):
        """
        set the stderr of the analyzer
        """
        self.__analyzer_stderr = stderr

    @property
    def analyzed_source_file(self):
        """
        the source file which is analyzed
        """
        return self.__analyzed_source_file

    @analyzed_source_file.setter
    def analyzed_source_file(self, file_path):
        """
        the source file which is analyzed
        """
        self.__analyzed_source_file = file_path

    def get_analyzer_result_file(self):
        """
        generate a result filename where the analyzer should put the analyzer result
        result file should be removed by the result handler if not required anymore
        """
        if not self.__res_file:
            analyzed_file = self.analyzed_source_file
            _, analyzed_file_name = ntpath.split(analyzed_file)

            uid = str(uuid.uuid1()).split('-')[0]

            out_file_name = str(self.buildaction.analyzer_type) + \
                '_' + analyzed_file_name + '_' + uid + '.plist'

            out_file = os.path.join(self.__workspace, out_file_name)
            self.__res_file = out_file

        return self.__res_file

    def clean_results(self):
        """
        should be called after the postprocessing and result handling is done
        """
        if self.__res_file:
            try:
                os.remove(self.__res_file)
            except OSError as oserr:
                # there might be no result file if analysis failed
                LOG.debug(oserr)
                pass


    @abstractmethod
    def postprocess_result(self):
        """
        postprocess result if needed
        should be called after the analisys finished
        """
        pass

    @abstractmethod
    def handle_results(self):
        """
        handle the results
        """
        pass
