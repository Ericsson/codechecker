# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import ntpath
import os
import shutil
from abc import ABCMeta

from codechecker_lib import plist_parser
from codechecker_lib.logger import LoggerFactory
from codechecker_lib.analyzers.result_handler_base import ResultHandler

LOG = LoggerFactory.get_new_logger('PLIST TO FILE')


class PlistToFile(ResultHandler):
    """
    Result handler for copying a plist file to a different location.
    """

    __metaclass__ = ABCMeta

    def __init__(self, buildaction, workspace, export_plist_path):
        super(PlistToFile, self).__init__(buildaction, workspace)
        self.__folder = export_plist_path

    @property
    def print_steps(self):
        """
        Print the multiple steps for a bug if there is any.
        """
        return self.__print_steps

    @print_steps.setter
    def print_steps(self, value):
        """
        Print the multiple steps for a bug if there is any.
        """
        self.__print_steps = value

    def handle_results(self):
        """This handler copies the plist file into the jailed_root."""
        plist = self.analyzer_result_file

        try:
            files, _ = plist_parser.parse_plist(plist)
        except Exception as ex:
            LOG.error('The generated plist is not valid!')
            LOG.error(ex)
            return 1

        err_code = self.analyzer_returncode

        if len(files) == 0:
            LOG.debug("Will not export '" +
                      plist + "', because plist is empty.")
            return err_code

        if err_code == 0:
            shutil.copy(plist, os.path.join(self.__folder,
                                            os.path.basename(plist)))
            LOG.debug("Exported '" + os.path.basename(plist) + "'")
        else:
            LOG.error('Analyzing %s with %s failed.\n' %
                      (ntpath.basename(self.analyzed_source_file),
                       self.buildaction.analyzer_type))
        return err_code

    def postprocess_result(self):
        """
        No postprocessing required for plists.
        """
        pass
