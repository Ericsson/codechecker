# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
CTU-specific test decorators.
"""

from functools import partial
from .decorators import make_skip_unless_attribute_found


NO_CTU_MESSAGE = "CTU is not supported"
NO_CTU_ON_DEMAND_MESSAGE = "CTU-on-demand is not supported"
NO_CTU_DISPLAY_PROGRESS_MESSAGE = "CTU diplay progress is not supported"

makeSkipUnlessCTUCapable = partial(make_skip_unless_attribute_found,
                                   message=NO_CTU_MESSAGE)

makeSkipUnlessCTUOnDemandCapable = partial(make_skip_unless_attribute_found,
                                           message=NO_CTU_ON_DEMAND_MESSAGE)

makeSkipUnlessCTUDisplayCapable = partial(
    make_skip_unless_attribute_found,
    message=NO_CTU_DISPLAY_PROGRESS_MESSAGE)
