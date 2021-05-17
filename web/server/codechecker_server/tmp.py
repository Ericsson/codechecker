# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Temporary directory module.
"""


import datetime
import hashlib
import os
import shutil
import tempfile


from codechecker_common.logger import get_logger

LOG = get_logger('system')


class TemporaryDirectory:
    def __init__(self, suffix='', prefix='tmp', tmp_dir=None):
        self._closed = False
        self.name = tempfile.mkdtemp(suffix, prefix, tmp_dir)

    def __enter__(self):
        return self.name

    def __cleanup(self):
        if self.name and not self._closed:
            try:
                shutil.rmtree(self.name)
            except (TypeError, AttributeError) as ex:
                print("ERROR: {0} while cleaning up {1}".format(ex, self.name))
                return
            self._closed = True

    def __exit__(self, *args):
        self.__cleanup()

    def __del__(self, *args):
        self.__cleanup()


def get_tmp_dir_hash():
    """Generate a hash based on the current time and process id."""

    pid = os.getpid()
    time = datetime.datetime.now()

    data = str(pid) + str(time)

    dir_hash = hashlib.md5()
    dir_hash.update(data.encode("utf-8"))

    LOG.debug('The generated temporary directory hash is %s.',
              dir_hash.hexdigest())

    return dir_hash.hexdigest()
