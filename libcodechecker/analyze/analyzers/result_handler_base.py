# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from abc import ABCMeta
import os
import uuid

from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('RESULT_HANDLER_BASE')


class ResultHandler(object):
    """
    Handle and store the results at runtime for the analyzer:
    stdout, stderr, temporarily generated files.
    Do result postprocessing if required.

    For each buildaction there is one result handler.
    The result handler can handle multiple results if there
    are more than one analyzed source file in one buildaction.

    handle_results() handles the results of a static analysis tool processed on
    a build action.

    For each build action
    - postprocess_result and handle_results can be called multiple times
      for the source files in one buildaction they will be analyzed separately
      with the same build options.

    Method call order should be:
    postprocess_result()
    handle_results()
    """

    __metaclass__ = ABCMeta
    # Handle the output stdout, or plist or both for an analyzer.

    def __init__(self, action, workspace):
        """
        Put the temporary files for the workspace.
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

        self.__result_file = None

    @property
    def buildaction(self):
        """
        """
        return self.__buildaction

    @property
    def analyzer_cmd(self):
        """
        Set the analyzer cmd.
        """
        return self.__analyzer_cmd

    @analyzer_cmd.setter
    def analyzer_cmd(self, cmd):
        """
        Set the analyzer cmd.
        """
        self.__analyzer_cmd = cmd

    @property
    def skiplist_handler(self):
        """
        """
        return self.__skiplist_handler

    @skiplist_handler.setter
    def skiplist_handler(self, handler):
        """
        Used to check if analyzer result should be
        handled or just skipped.
        """
        self.__skiplist_handler = handler

    @property
    def severity_map(self):
        """
        Severity map for each checker.
        """
        return self.__severity_map

    @severity_map.setter
    def severity_map(self, value):
        """
        Severity map for each checker.
        """
        self.__severity_map = value

    @property
    def workspace(self):
        """
        Workspace where the analysis results and temporarily generated files
        should go.
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
        Get the stdout from the analyzer.
        """
        return self.__analyzer_stdout

    @analyzer_stdout.setter
    def analyzer_stdout(self, stdout):
        """
        Set the stdout of the analyzer.
        """
        self.__analyzer_stdout = stdout

    @property
    def analyzer_stderr(self):
        """
        Get stderr of the analyzer.
        """
        return self.__analyzer_stderr

    @analyzer_stderr.setter
    def analyzer_stderr(self, stderr):
        """
        Set the stderr of the analyzer.
        """
        self.__analyzer_stderr = stderr

    @property
    def analyzed_source_file(self):
        """
        The source file which is analyzed.
        """
        return self.__analyzed_source_file

    @analyzed_source_file.setter
    def analyzed_source_file(self, file_path):
        """
        The source file which is analyzed.
        """
        self.__analyzed_source_file = file_path

    @property
    def analyzer_result_file(self):
        """
        Generate a result filename where the analyzer should put the results.
        Result file should be removed by the result handler eventually.
        """
        if not self.__result_file:
            analyzed_file = self.analyzed_source_file
            _, analyzed_file_name = os.path.split(analyzed_file)

            uid = str(uuid.uuid1()).split('-')[0]

            out_file_name = str(self.buildaction.analyzer_type) + \
                '_' + analyzed_file_name + '_' + uid + '.plist'

            out_file = os.path.join(self.__workspace, out_file_name)
            self.__result_file = out_file

        return self.__result_file

    @analyzer_result_file.setter
    def analyzer_result_file(self, file_path):
        """
        The result of the analysis which will be processed afterwards.
        """
        self.__result_file = file_path

    def clean_results(self):
        """
        Should be called after the postprocessing and result handling is done.
        """
        if self.__result_file:
            try:
                os.remove(self.__result_file)
            except OSError as oserr:
                # There might be no result file if analysis failed.
                LOG.debug(oserr)

    def postprocess_result(self):
        """
        Postprocess result if needed.
        Should be called after the analyses finished.
        """
        pass

    def handle_results(self, client):
        """
        Handle the results.
        """
        pass
