# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
""""""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def get_check_env(path_env_extra, ld_lib_path_extra):
    """
    Extending the checker environment.
    Check environment is extended to find tools if they ar not on
    the default places.
    """
    new_env = os.environ.copy()

    if path_env_extra:
        extra_path = ':'.join(path_env_extra)
        LOG.debug_analyzer(
            'Extending PATH environment variable with: ' + extra_path)

        try:
            new_env['PATH'] = extra_path + ':' + new_env['PATH']
        except KeyError:
            new_env['PATH'] = extra_path

    if ld_lib_path_extra:
        extra_lib = ':'.join(ld_lib_path_extra)
        LOG.debug_analyzer(
            'Extending LD_LIBRARY_PATH environment variable with: ' +
            extra_lib)
        try:
            original_ld_library_path = new_env['LD_LIBRARY_PATH']
            new_env['LD_LIBRARY_PATH'] = \
                extra_lib + ':' + original_ld_library_path
        except KeyError:
            new_env['LD_LIBRARY_PATH'] = extra_lib

    return new_env
