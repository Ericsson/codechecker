# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------


import glob
import logging
import os
import plistlib

from codechecker_report_converter.analyzer_result import AnalyzerResult
from codechecker_report_converter.report import generate_report_hash


LOG = logging.getLogger('ReportConverter')


class CppcheckAnalyzerResult(AnalyzerResult):
    """ Transform analyzer result of Cppcheck. """

    TOOL_NAME = 'cppcheck'
    NAME = 'Cppcheck'
    URL = 'http://cppcheck.sourceforge.net'

    def parse(self, analyzer_result):
        """ Creates plist objects from the given analyzer result.

        Returns a list of plist objects.
        """
        plist_files = []
        if os.path.isdir(analyzer_result):
            plist_files = glob.glob(os.path.join(analyzer_result, "*.plist"))
        elif os.path.isfile(analyzer_result) and \
                analyzer_result.endswith(".plist"):
            plist_files = [analyzer_result]
        else:
            LOG.error("The given input should be an existing CppCheck result "
                      "directory or a plist file.")
            return None

        file_to_plist_data = {}
        for f in plist_files:
            plist_file = os.path.basename(f)
            file_name = '{0}_{1}.plist'.format(os.path.splitext(plist_file)[0],
                                               self.TOOL_NAME)
            with open(f, 'rb') as plist_file:
                file_to_plist_data[file_name] = plistlib.load(plist_file)

        return file_to_plist_data

    def _add_report_hash(self, file_to_plist_data):
        """ Generate report hash for each diagnostics in the plist objects.

        It will generate a context free hash for each diagnostics.
        """
        for file_name, plist_data in file_to_plist_data.items():
            files = plist_data['files']

            is_changed = False
            for diag in plist_data['diagnostics']:
                report_hash = diag.get('issue_hash_content_of_line_in_context')
                if not report_hash or report_hash == '0':
                    report_hash = \
                        generate_report_hash(diag,
                                             files[diag['location']['file']])
                    diag['issue_hash_content_of_line_in_context'] = report_hash
                    is_changed = True

            if not is_changed:
                LOG.info("Plist file is up to date: '%s'", file_name)
                file_to_plist_data[file_name] = None

    def _write(self, file_to_plist_data, output_dir):
        """ Creates plist files from the parse result to the given output. """
        output_dir = os.path.abspath(output_dir)
        for file_name, plist_data in file_to_plist_data.items():
            if not plist_data:
                continue

            out_file = os.path.join(output_dir, file_name)

            LOG.info("Modify plist file: '%s'.", out_file)
            LOG.debug(plist_data)

            try:
                with open(out_file, 'wb') as plist_file:
                    plistlib.dump(plist_data, plist_file)
            except TypeError as err:
                LOG.error('Failed to write plist file: %s', out_file)
                LOG.error(err)
