# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


class CheckerLabels:
    def severity(self, a: str, b: str | None = None) -> str:
        raise NotImplementedError()

    def label_of_checker(self, a: str, b: str, c: str | None = None) -> str:
        raise NotImplementedError()
