# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Config handler for Cppcheck analyzer.
"""
from .. import config_handler


class CppcheckConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for Cppcheck analyzer.
    """
