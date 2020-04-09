# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------


from abc import ABCMeta, abstractmethod
import logging
import os
import plistlib

from . import __title__, __version__
from .report import generate_report_hash

LOG = logging.getLogger('ReportConverter')


class AnalyzerResult(object, metaclass=ABCMeta):
    """ Base class to transform analyzer result. """

    # Short name of the analyzer.
    TOOL_NAME = None

    # Full name of the analyzer.
    NAME = None

    # Link to the official analyzer website.
    URL = None

    def transform(self, analyzer_result, output_dir):
        """ Creates plist files from the given analyzer result to the given
        output directory.
        """
        analyzer_result = os.path.abspath(analyzer_result)
        plist_objs = self.parse(analyzer_result)
        if not plist_objs:
            LOG.info("No '%s' results can be found in the given code analyzer "
                     "output.", self.TOOL_NAME)
            return False

        self._post_process_result(plist_objs)

        self._write(plist_objs, output_dir)

        return True

    @abstractmethod
    def parse(self, analyzer_result):
        """ Creates plist objects from the given analyzer result.

        Returns a list of plist objects.
        """
        raise NotImplementedError("Subclasses should implement this!")

    def _post_process_result(self, plist_objs):
        """ Post process the parsed result.

        By default it will add report hashes and metada information for the
        diagnostics.
        """
        for plist_obj in plist_objs:
            self._add_report_hash(plist_obj)
            self._add_metadata(plist_obj)

    def _add_report_hash(self, plist_obj):
        """ Generate report hash for the given plist data. """
        files = plist_obj['files']
        for diag in plist_obj['diagnostics']:
            report_hash = \
                generate_report_hash(diag,
                                     files[diag['location']['file']])
            diag['issue_hash_content_of_line_in_context'] = report_hash

    def _add_metadata(self, plist_obj):
        """ Add metada information to the given plist data. """
        plist_obj['metadata'] = {
            'analyzer': {
                'name': self.TOOL_NAME
            },
            'generated_by': {
                'name': __title__,
                'version': __version__
            }
        }

    def _get_analyzer_result_file_content(self, result_file):
        """ Return the content of the given file. """
        if not os.path.exists(result_file):
            LOG.error("Result file does not exists: %s", result_file)
            return

        if os.path.isdir(result_file):
            LOG.error("Directory is given instead of a file: %s", result_file)
            return

        with open(result_file, 'r', encoding='utf-8',
                  errors='replace') as analyzer_result:
            return analyzer_result.readlines()

    def _write(self, plist_objs, output_dir):
        """ Creates plist files from the parse result to the given output.

        It will generate a context free hash for each diagnostics.
        """
        output_dir = os.path.abspath(output_dir)
        for plist_data in plist_objs:
            file_name = os.path.basename(plist_data['files'][0])
            out_file_name = '{0}_{1}.plist'.format(file_name, self.TOOL_NAME)
            out_file = os.path.join(output_dir, out_file_name)

            LOG.info("Create/modify plist file: '%s'.", out_file)
            LOG.debug(plist_data)

            try:
                with open(out_file, 'wb') as plist_file:
                    plistlib.dump(plist_data, plist_file)
            except TypeError as err:
                LOG.error('Failed to write plist file: %s', out_file)
                LOG.error(err)
