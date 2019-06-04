# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Util module.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import io
import json
import os
import re
import time

from threading import Timer

import portalocker
import psutil

from codechecker_common.logger import get_logger

LOG = get_logger('system')


class RawDescriptionDefaultHelpFormatter(
        argparse.RawDescriptionHelpFormatter,
        argparse.ArgumentDefaultsHelpFormatter
):
    """
    Adds default values to argument help and retains any formatting in
    descriptions.
    """
    pass


def find_by_regex_in_envpath(pattern, environment):
    """
    Searches for files matching the pattern string in the environment's PATH.
    """

    regex = re.compile(pattern)

    binaries = {}
    for path in environment['PATH'].split(os.pathsep):
        _, _, filenames = next(os.walk(path), ([], [], []))
        for f in filenames:
            if re.match(regex, f):
                if binaries.get(f) is None:
                    binaries[f] = [os.path.join(path, f)]
                else:
                    binaries[f].append(os.path.join(path, f))

    return binaries


def get_binary_in_path(basename_list, versioning_pattern, env):
    """
    Select the most matching binary for the given pattern in the given
    environment. Works well for binaries that contain versioning.
    """

    binaries = find_by_regex_in_envpath(versioning_pattern, env)

    if not binaries:
        return False
    elif len(binaries) == 1:
        # Return the first found (earliest in PATH) binary for the only
        # found binary name group.
        return list(binaries.values())[0][0]
    else:
        keys = list(binaries.keys())
        keys.sort()

        # If one of the base names match, select that version.
        files = None
        for base_key in basename_list:
            # Cannot use set here as it would destroy precendence.
            if base_key in keys:
                files = binaries[base_key]
                break

        if not files:
            # Select the "newest" available version if there are multiple and
            # none of the base names matched.
            files = binaries[keys[-1]]

        # Return the one earliest in PATH.
        return files[0]


def kill_process_tree(parent_pid, recursive=False):
    proc = psutil.Process(parent_pid)
    children = proc.children(recursive)

    # Send a SIGTERM (Ctrl-C) to the main process
    proc.terminate()

    # If children processes don't stop gracefully in time,
    # slaughter them by force.
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


def setup_process_timeout(proc, timeout,
                          failure_callback=None):
    """
    Setup a timeout on a process. After `timeout` seconds, the process is
    killed by `signal_at_timeout` signal.

    :param proc: The subprocess.Process object representing the process to
      attach the watcher to.
    :param timeout: The timeout the process is allowed to run for, in seconds.
      This timeout is counted down some moments after calling
      setup_process_timeout(), and due to OS scheduling, might not be exact.
    :param failure_callback: An optional function which is called when the
      process is killed by the timeout. This is called with no arguments
      passed.

    :return: A function is returned which should be called when the client code
      (usually via subprocess.Process.wait() or
      subprocess.Process.communicate())) figures out that the called process
      has terminated. (See below for what this called function returns.)
    """

    # The watch dict encapsulated the captured variables for the timeout watch.
    watch = {'pid': proc.pid,
             'timer': None,  # Will be created later.
             'counting': False,
             'killed': False}

    def __kill():
        """
        Helper function to execute the killing of a hung process.
        """
        LOG.debug("Process %s has ran for too long, killing it!",
                  watch['pid'])
        watch['counting'] = False
        watch['killed'] = True
        kill_process_tree(watch['pid'], True)

        if failure_callback:
            failure_callback()

    timer = Timer(timeout, __kill)
    watch['timer'] = timer

    LOG.debug("Setup timeout of %s for PID %s", proc.pid, timeout)
    timer.start()
    watch['counting'] = True

    def __cleanup_timeout():
        """
        Stops the timer associated with the timeout watch if the process
        finished within the grace period.

        Due to race conditions and the possibility of the OS, or another
        process also using signals to kill the watched process in particular,
        it is possible that checking subprocess.Process.returncode on the
        watched process is not enough to see if the timeout watched killed it,
        or something else.

        (Note: returncode is -N where N is the signal's value, but only on Unix
        systems!)

        It is safe to call this function multiple times to check for the result
        of the watching.

        :return: Whether or not the process was killed by the watcher. If this
          is False, the process could have finished gracefully, or could have
          been destroyed by other means.
        """
        if watch['counting'] and not watch['killed'] and watch['timer']:
            watch['timer'].cancel()
            watch['timer'] = None
            watch['counting'] = False

        return watch['killed']

    return __cleanup_timeout


def arg_match(options, args):
    """Checks and selects the option string specified in 'options'
    that are present in parameter 'args'."""
    matched_args = []
    for option in options:
        if any([arg if option.startswith(arg) else None
                for arg in args]):
            matched_args.append(option)
            continue

    return matched_args


def get_line(file_name, line_no, errors='ignore'):
    """
    Return the given line from the file. If line_no is larger than the number
    of lines in the file then empty string returns.
    If the file can't be opened for read, the function also returns empty
    string.

    Try to encode every file as utf-8 to read the line content do not depend
    on the platform settings. By default locale.getpreferredencoding() is used
    which depends on the platform.

    Changing the encoding error handling can influence the hash content!
    """
    try:
        with io.open(file_name, mode='r',
                     encoding='utf-8',
                     errors=errors) as source_file:
            for line in source_file:
                line_no -= 1
                if line_no == 0:
                    return line
            return u''
    except IOError:
        LOG.error("Failed to open file %s", file_name)
        return u''


def load_json_or_empty(path, default=None, kind=None, lock=False):
    """
    Load the contents of the given file as a JSON and return it's value,
    or default if the file can't be loaded.
    """

    ret = default
    try:
        with io.open(path, 'r') as handle:
            if lock:
                portalocker.lock(handle, portalocker.LOCK_SH)

            ret = json.loads(handle.read())

            if lock:
                portalocker.unlock(handle)
    except IOError as ex:
        LOG.warning("Failed to open %s file: %s",
                    kind if kind else 'json',
                    path)
        LOG.warning(ex)
    except OSError as ex:
        LOG.warning("Failed to open %s file: %s",
                    kind if kind else 'json',
                    path)
        LOG.warning(ex)
    except ValueError as ex:
        LOG.warning("'%s' is not a valid %s file.",
                    kind if kind else 'json',
                    path)
        LOG.warning(ex)
    except TypeError as ex:
        LOG.warning('Failed to process json file: %s', path)
        LOG.warning(ex)

    return ret


def get_last_mod_time(file_path):
    """
    Return the last modification time of a file.
    """
    try:
        return os.stat(file_path).st_mtime
    except OSError as oerr:
        LOG.debug(oerr)
        LOG.debug("File is missing")
        return None


def trim_path_prefixes(path, prefixes):
    """
    Removes the longest matching leading path from the file path.
    """

    # If no prefixes are specified.
    if not prefixes:
        return path

    # Find the longest matching prefix in the path.
    longest_matching_prefix = None
    for prefix in prefixes:
        if not prefix.endswith('/'):
            prefix += '/'

        if path.startswith(prefix) and (not longest_matching_prefix or
                                        longest_matching_prefix < prefix):
            longest_matching_prefix = prefix

    # If no prefix found or the longest prefix is the root do not trim the
    # path.
    if not longest_matching_prefix or longest_matching_prefix == '/':
        return path

    return path[len(longest_matching_prefix):]
