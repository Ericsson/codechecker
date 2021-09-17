# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Instance manager handles the state keeping of running CodeChecker instances
for a particular user on the local machine.
"""


import getpass
import json
import os
import psutil
import socket
import stat

import portalocker

from codechecker_report_converter.util import load_json_or_empty

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def __get_instance_descriptor_path(folder=None):
    if not folder:
        folder = os.path.expanduser("~")

    return os.path.join(folder, ".codechecker.instances.json")


def __make_instance_descriptor_file(folder=None):
    descriptor = __get_instance_descriptor_path(folder)
    if not os.path.exists(descriptor):
        with open(descriptor, 'w',
                  encoding="utf-8", errors="ignore") as f:
            json.dump([], f)
        os.chmod(descriptor, stat.S_IRUSR | stat.S_IWUSR)


def __check_instance(hostname, pid):
    """Check if the given process on the system is a valid, running CodeChecker
    for the current user."""

    # Instances running on a remote host with a filesystem shared with us can
    # not usually be checked (/proc is rarely shared across computers...),
    # so we consider them "alive" servers.
    if hostname != socket.gethostname():
        return True

    try:
        proc = psutil.Process(pid)

        cli = os.path.join("codechecker_common", "cli.py")
        return cli in proc.cmdline()[1] and \
            proc.username() == getpass.getuser()
    except psutil.NoSuchProcess:
        # If the process does not exist, it cannot be valid.
        return False


def __rewrite_instance_file(append, remove, folder=None):
    """
    This helper method reads the user's instance descriptor and manages it
    eliminating dead records, appending new ones and re-serialising the file.
    """
    __make_instance_descriptor_file(folder)

    append_pids = [i['pid'] for i in append]

    instance_descriptor_file = __get_instance_descriptor_path(folder)
    with open(instance_descriptor_file, 'r+',
              encoding="utf-8", errors="ignore") as instance_file:
        portalocker.lock(instance_file, portalocker.LOCK_EX)

        instances = []
        try:
            instances = json.loads(instance_file.read())
        except (ValueError, TypeError) as ex:
            LOG.warning('Failed to process json file: %s',
                        instance_descriptor_file)
            LOG.warning(ex)

        # After reading, check every instance if they are still valid and
        # make sure PID does not collide accidentally with the
        # to-be-registered instances, if any exists in the append list as it
        # would cause duplication.
        #
        # Also, we remove the records to the given PIDs, if any exists.
        instances = [i for i in instances
                     if i['pid'] not in append_pids and
                     (i['hostname'] + ":" + str(i['pid'])) not in remove]

        instances = instances + append

        instance_file.seek(0)
        instance_file.truncate()
        json.dump(instances, instance_file, indent=2)
        portalocker.unlock(instance_file)


def register(pid, workspace, port, folder=None):
    """
    Adds the specified CodeChecker server instance to the user's instance
    descriptor.
    """

    __rewrite_instance_file([{"pid": pid,
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

    __rewrite_instance_file([],
                            [socket.gethostname() + ":" + str(pid)],
                            folder)


def get_instances(folder=None):
    """Returns the list of running servers for the current user."""

    # This method does NOT write the descriptor file.

    descriptor = __get_instance_descriptor_path(folder)
    instances = load_json_or_empty(descriptor, {}, lock=True)

    return [i for i in instances if __check_instance(i['hostname'], i['pid'])]
