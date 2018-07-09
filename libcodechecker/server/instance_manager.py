# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Instance manager handles the state keeping of running CodeChecker instances
for a particular user on the local machine.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import getpass
import json
import os
import portalocker
import psutil
import socket
import stat
from libcodechecker.logger import get_logger

LOG = get_logger('server')


def __getInstanceDescriptorPath(folder=None):
    if not folder:
        folder = os.path.expanduser("~")

    return os.path.join(folder, ".codechecker.instances.json")


def __makeInstanceDescriptorFile(folder=None):
    descriptor = __getInstanceDescriptorPath(folder)
    if not os.path.exists(descriptor):
        with open(descriptor, 'w') as f:
            json.dump([], f)
        os.chmod(descriptor, stat.S_IRUSR | stat.S_IWUSR)


def __checkInstance(hostname, pid):
    """Check if the given process on the system is a valid, running CodeChecker
    for the current user."""

    # Instances running on a remote host with a filesystem shared with us can
    # not usually be checked (/proc is rarely shared across computers...),
    # so we consider them "alive" servers.
    if hostname != socket.gethostname():
        return True

    try:
        proc = psutil.Process(pid)

        return "CodeChecker.py" in proc.cmdline()[1] and \
               proc.username() == getpass.getuser()
    except psutil.NoSuchProcess:
        # If the process does not exist, it cannot be valid.
        return False


def __rewriteInstanceFile(append, remove, folder=None):
    """This helper method reads the user's instance descriptor and manages it
    eliminating dead records, appending new ones and reserialising the file."""

    __makeInstanceDescriptorFile(folder)
    with open(__getInstanceDescriptorPath(folder), 'r+') as f:
        portalocker.lock(f, portalocker.LOCK_EX)

        # After reading, check every instance if they are still valid and
        # make sure PID does not collide accidentally with the
        # to-be-registered instances, if any exists in the append list as it
        # would cause duplication.
        #
        # Also, we remove the records to the given PIDs, if any exists.
        append_pids = [i['pid'] for i in append]
        try:
            instances = [i for i in json.load(f)
                         if i['pid'] not in append_pids and
                         (i['hostname'] + ":" + str(i['pid'])) not in remove and
                         __checkInstance(i['hostname'], i['pid'])]
        except ValueError:
            LOG.error("Failed to load json file:")
            LOG.error(f)

        instances = instances + append

        f.seek(0)
        f.truncate()
        json.dump(instances, f, indent=2)
        portalocker.unlock(f)


def register(pid, workspace, port, folder=None):
    """
    Adds the specified CodeChecker server instance to the user's instance
    descriptor.
    """

    __rewriteInstanceFile([{"pid": pid,
                            "hostname": socket.gethostname(),
                            "workspace": workspace,
                            "port": port}],
                          [],
                          folder)


def unregister(pid, folder=None):
    """
    Removes the specified CodeChecker server instance from the user's instance
    descriptor.
    """

    __rewriteInstanceFile([], [socket.gethostname() + ":" + str(pid)], folder)


def get_instances(folder=None):
    """Returns the list of running servers for the current user."""

    # This method does NOT write the descriptor file.

    descriptor = __getInstanceDescriptorPath(folder)
    instances = []
    if os.path.exists(descriptor):
        with open(descriptor, 'r') as f:
            portalocker.lock(f, portalocker.LOCK_SH)
            instances = [i for i in json.load(f) if __checkInstance(
                i['hostname'],
                i['pid'])]
            portalocker.unlock(f)

    return instances
