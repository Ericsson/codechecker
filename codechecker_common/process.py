# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import time

import psutil

from .logger import get_logger


LOG = get_logger("system")


def kill_process_tree(parent_pid, recursive=False):
    """
    Stop the process tree, gracefully at first.

    Try to stop the parent and child processes gracefuly first.
    If they do not stop in time, send a kill signal to every member of the
    process tree.
    """
    proc = psutil.Process(parent_pid)
    children = proc.children(recursive)

    # Send a SIGTERM to the main process.
    proc.terminate()

    # If children processes don't stop gracefully in time, slaughter them
    # by force.
    _, still_alive = psutil.wait_procs(children, timeout=5)
    for p in still_alive:
        p.kill()

    # Wait until this process is running.
    n = 0
    timeout = 10
    while proc.is_running():
        if n > timeout:
            LOG.warning("Waiting for process %s to stop has been timed out"
                        "(timeout = %s)! Process is still running!",
                        parent_pid, timeout)
            break

        time.sleep(1)
        n += 1
