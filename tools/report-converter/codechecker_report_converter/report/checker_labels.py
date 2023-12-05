# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from typing import Callable, List, Optional, Union


class CheckerLabels:
    severity: Callable[[str], str]
    label_of_checker: Callable[
        [str, str, Optional[str]], Union[str, List[str]]]
