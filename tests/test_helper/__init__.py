#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import os
import sys

def set_cc_env():
    cc_root = os.environ['CC_PACKAGE_ROOT']
    sys.path.append(os.path.join(ccRoot, 'lib/python2.7/report-viewer'))
    sys.path.append(os.path.join(ccRoot, 'lib/python2.7/report-server'))
    sys.path.append(os.path.join(ccRoot, 'lib/python2.7'))
    sys.path.append(os.path.join(ccRoot, 'python/lib/python2.7'))

    os.environ['LD_LIBRARY_PATH'] = os.path.join(ccRoot, 'python/lib/python2.7/lib-dynload') + ':' \
                                    + os.path.join(ccRoot, 'postgres/lib') + ':' + os.getenv('LD_LIBRARY_PATH', '')

def get_free_port():
    ''' get a free port from the os'''

    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    free_port = s.getsockname()[1]
    s.close()

    return free_port
