# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Clang Static analyzer configuration handler.
"""
from codechecker_common.logger import get_logger

from .. import config_handler

LOG = get_logger('analyzer.clangsa')


class ClangSAConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for the clang static analyzer.
    """

    def __init__(self, environ):
        super().__init__()
        self.ctu_dir = ''
        self.ctu_on_demand = False
        self.enable_z3 = False
        self.enable_z3_refutation = False
        self.environ = environ
        self.analyze_headers = False
        self.expand_macros = False
