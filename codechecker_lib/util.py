# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Util module.
"""

import datetime
import os
import hashlib
import ntpath
import sys
import glob
import socket
import shutil
import subprocess

from codechecker_lib import logger

# WARNING! LOG should be only used in this module.
LOG = logger.get_new_logger('UTIL')


# ---------------------------------------------------------------------
def get_free_port():
    """ Get a free port from the OS. """

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    free_port = s.getsockname()[1]
    s.close()

    return free_port


# ---------------------------------------------------------------------
def is_localhost(address):
    """
    Check if address is one of the valid values and try to get the
    IP-addresses from the system.
    """

    valid_values = ['localhost', '0.0.0.0', '*']

    try:
        valid_values.append(socket.gethostbyname('localhost'))
    except Exception:
        # Failed to get ip address for localhost.
        pass

    try:
        valid_values.append(socket.gethostbyname(socket.gethostname()))
    except Exception:
        # Failed to get ip address for host_name.
        pass

    return address in valid_values


# ---------------------------------------------------------------------
def match_file_name(file_name, pattern):
    file_name_parts = file_name.split('--')

    if file_name_parts[0] == pattern:
        return True
    else:
        return False


# ---------------------------------------------------------------------
def get_file_last_modification_time(file):
    """
    Returns the last modification time of a file.
    """
    return datetime.datetime.fromtimestamp(os.path.getmtime(file))


# ---------------------------------------------------------------------
def get_env_var(env_var, needed=False):
    """
    Read the environment variables and handle the exception if a necessary
    environment variable is missing.
    """

    value = os.getenv(env_var)
    if needed and not value:
        LOG.critical('Failed to read necessary environment variable %s.'
                     ' (Maybe codechecker was not configured properly)'
                     % env_var)
        sys.exit(1)

    return value


# -------------------------------------------------------------------------
def get_tmp_dir_hash():
    """Generate a hash based on the current time and process id."""

    pid = os.getpid()
    time = datetime.datetime.now()

    data = str(pid) + str(time)

    dir_hash = hashlib.md5()
    dir_hash.update(data)

    LOG.debug('The generated temporary directory hash is %s'
              % dir_hash.hexdigest())

    return dir_hash.hexdigest()


# -------------------------------------------------------------------------
def get_file_name_from_path(path):
    """Get the filename from a path."""
    head, tail = ntpath.split(path)
    return head, tail


# -------------------------------------------------------------------------
def get_obj_target(object_file_path):
    return os.path.split(os.path.abspath(dir))[-2]


# -------------------------------------------------------------------------
def create_dir(path):
    """Create a directory safely if it does not exist yet.
    This may be called from several processes or threads, creating the same
    directory, and it fails only if the directory is not created.
    """

    if not os.path.isdir(path):
        try:
            LOG.debug('Creating directory %s' % path)
            os.makedirs(path)
        except Exception as e:
            if not os.path.isdir(path):
                LOG.error('Failed to create directory %s' % path)
                raise e

    return


# -------------------------------------------------------------------------
def get_file_list(path, pattern):
    glob_pattern = os.path.join(path, pattern)
    return glob.glob(glob_pattern)


# -------------------------------------------------------------------------
def remove_file_list(file_list):
    for rfile in file_list:
        LOG.debug(rfile)
        try:
            os.remove(rfile)
        except OSError:
            # Maybe another thread has already deleted it.
            LOG.debug('Failed to remove file %s' % rfile)

    return


# -------------------------------------------------------------------------
def remove_dir(path):
    def error_handler(*args):
        LOG.warning('Failed to remove directory %s' % path)

    shutil.rmtree(path, onerror=error_handler)


def call_command(command, env=None):
    """ Call an external command and return with (output, return_code)."""

    try:
        LOG.debug('Run ' + ' '.join(command))
        out = subprocess.check_output(command,
                                      bufsize=-1,
                                      env=env,
                                      stderr=subprocess.STDOUT)
        LOG.debug(out)
        return out, 0
    except subprocess.CalledProcessError as ex:
        LOG.debug('Running command "' + ' '.join(command) + '" Failed')
        LOG.debug(str(ex.returncode))
        LOG.debug(ex.output)
        return ex.output, ex.returncode


def get_default_workspace():
    """
    Default workspace in the users home directory.
    """
    workspace = os.path.join(os.path.expanduser("~"), '.codechecker')
    return workspace
