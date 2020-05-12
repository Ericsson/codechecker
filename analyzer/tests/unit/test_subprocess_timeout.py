# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test if the subprocess timeout watcher works properly.
"""


import os
import signal
import subprocess
import unittest

import psutil

from codechecker_analyzer.analysis_manager import setup_process_timeout


class subprocess_timeoutTest(unittest.TestCase):
    """
    Test the process timeout watcher functionality.
    """

    def testTimeoutWithProcessFinishing(self):
        """
        Test if process timeout watcher recognises if a process ended
        gracefully before the timeout expired.
        """
        # Create a process that executes quickly.
        proc = subprocess.Popen(['echo',
                                 'This process executes quickly!'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                preexec_fn=os.setpgrp,
                                encoding="utf-8",
                                errors="ignore")
        print("Started `echo` with PID {0}".format(proc.pid))

        future = setup_process_timeout(proc, 5, signal.SIGKILL)

        # Simulate waiting for the process.
        proc.wait()

        # Execution reaches this spot, the process exited, one way or another.
        killed = future()
        self.assertFalse(killed,
                         "Process timeout watcher said it killed the "
                         "process, but it should have exited long beforehand.")

    def testTimeoutWithLongRunning(self):
        """
        Test if process timeout watcher kills the process that runs too long,
        and properly reports that it was killed.
        """
        # Create a process that runs infinitely.
        proc = subprocess.Popen(['sh',
                                 '-c',
                                 'yes'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                preexec_fn=os.setpgrp,
                                encoding="utf-8",
                                errors="ignore")
        print("Started `yes` with PID {0}".format(proc.pid))

        future = setup_process_timeout(proc, 5)

        # Simulate waiting for the process.
        proc.wait()

        # Execution reaches this spot, which means the process was killed.
        # (Or it ran way too long and the OS killed it. Usually tests run
        # quick enough this isn't the case...)
        killed = future()
        self.assertTrue(killed,
                        "Process timeout watcher said it did not kill the "
                        "process, but it should have.")

        with self.assertRaises(psutil.NoSuchProcess):
            # Try to fetch the process from the system. It shouldn't exist.
            osproc = psutil.Process(proc.pid)

            # There can be rare cases that the OS so quickly recycles the PID.
            if osproc.exe() != 'yes':
                # (Let's just say it's very, very, VERY rare that it recycles
                # the PID to another execution of 'yes'...)

                # If the process exists but it isn't the process we started,
                # it's the same as if it doesn't existed.
                raise psutil.NoSuchProcess(proc.pid)

        # NOTE: This assertion is only viable on Unix systems!
        self.assertEqual(proc.returncode, -signal.SIGTERM,
                         "`yes` died in a way that it wasn't the process "
                         "timeout watcher killing it.")
