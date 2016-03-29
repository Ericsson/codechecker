#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import json
import os
import sys


def set_cc_env():
    cc_root = os.environ['CC_PACKAGE_ROOT']
    layout_file_path = os.path.join(cc_root, 'config', 'package_layout.json')

    with open(layout_file_path) as layout_file:
        package_layout = json.load(layout_file)

    gen_modules = \
        os.path.join(cc_root, package_layout['static']['codechecker_gen'])

    sys.path.append(gen_modules)


def get_free_port():
    ''' get a free port from the os'''

    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    free_port = s.getsockname()[1]
    s.close()

    return free_port
