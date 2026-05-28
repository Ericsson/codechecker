# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from .. import config_handler


class ClippyConfigHandler(config_handler.AnalyzerConfigHandler):
    """Configuration handler for Clippy analyzer."""

    def __init__(self):
        super().__init__()
        self.cargo_extra_arguments = []
        self.clippy_extra_arguments = []
