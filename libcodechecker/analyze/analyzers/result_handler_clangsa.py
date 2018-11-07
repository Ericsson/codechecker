# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Result handler for Clang Static Analyzer.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import plistlib
import sys
import traceback
from xml.parsers.expat import ExpatError

from libcodechecker.analyze.analyzers.result_handler_base \
    import ResultHandler
from libcodechecker.analyze.plist_parser import get_checker_name
from libcodechecker.logger import get_logger
from libcodechecker.report import generate_report_hash

LOG = get_logger('report')


def use_context_free_hashes(path):
    """
    Override issue hash in the given file by using context free hashes.
    """
    try:
        plist = plistlib.readPlist(path)

        files = plist['files']

        for diag in plist['diagnostics']:
            file_path = files[diag['location']['file']]

            report_hash = generate_report_hash(diag['path'],
                                               file_path,
                                               get_checker_name(diag))
            diag['issue_hash_content_of_line_in_context'] = report_hash

        if plist['diagnostics']:
            plistlib.writePlist(plist, path)

    except (ExpatError, TypeError, AttributeError) as err:
        LOG.warning('Failed to process plist file: %s wrong file format?',
                    path)
        LOG.warning(err)
    except IndexError as iex:
        LOG.warning('Indexing error during processing plist file %s', path)
        LOG.warning(type(iex))
        LOG.warning(repr(iex))
        _, _, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
    except Exception as ex:
        LOG.warning('Error during processing reports from the plist file: %s',
                    path)
        traceback.print_exc()
        LOG.warning(type(ex))
        LOG.warning(ex)


class ResultHandlerClangSA(ResultHandler):
    """
    Use context free hash if enabled.
    """

    def __init__(self, action, workspace):
        super(ResultHandlerClangSA, self).__init__(action, workspace)
        self.report_hash = None

    def postprocess_result(self):
        """
        Override the context sensitive issue hash in the plist files to
        context insensitive if it is enabled during analysis.
        """
        if self.report_hash == 'context-free':
            use_context_free_hashes(self.analyzer_result_file)
