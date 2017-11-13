# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Util module.
"""

import datetime
import hashlib
import os
import re
import socket
import subprocess

import psutil

from libcodechecker.logger import LoggerFactory

# WARNING! LOG should be only used in this module.
LOG = LoggerFactory.get_new_logger('UTIL')


def get_free_port():
    """ Get a free port from the OS. """

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    free_port = s.getsockname()[1]
    s.close()

    return free_port


def is_localhost(address):
    """
    Check if address is one of the valid values and try to get the
    IP-addresses from the system.
    """

    valid_values = ['localhost', '0.0.0.0', '*', '::1']

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


def get_tmp_dir_hash():
    """Generate a hash based on the current time and process id."""

    pid = os.getpid()
    time = datetime.datetime.now()

    data = str(pid) + str(time)

    dir_hash = hashlib.md5()
    dir_hash.update(data)

    LOG.debug('The generated temporary directory hash is %s.'
              % dir_hash.hexdigest())

    return dir_hash.hexdigest()


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

    if len(binaries) == 0:
        return False
    elif len(binaries) == 1:
        # Return the first found (earliest in PATH) binary for the only
        # found binary name group.
        return binaries.values()[0][0]
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


def call_command(command, env=None, cwd=None):
    """ Call an external command and return with (output, return_code)."""

    try:
        LOG.debug('Run ' + ' '.join(command))
        out = subprocess.check_output(command,
                                      bufsize=-1,
                                      env=env,
                                      stderr=subprocess.STDOUT,
                                      cwd=cwd)
        LOG.debug(out)
        return out, 0
    except subprocess.CalledProcessError as ex:
        LOG.debug('Running command "' + ' '.join(command) + '" Failed.')
        LOG.debug(str(ex.returncode))
        LOG.debug(ex.output)
        return ex.output, ex.returncode
    except OSError as oerr:
        LOG.warning(oerr.strerror)
        return oerr.strerror, oerr.errno


def kill_process_tree(parent_pid):
    proc = psutil.Process(parent_pid)
    children = proc.children()

    # Send a SIGTERM (Ctrl-C) to the main process
    proc.terminate()

    # If children processes don't stop gracefully in time,
    # slaughter them by force.
    __, still_alive = psutil.wait_procs(children, timeout=5)
    for p in still_alive:
        p.kill()


def get_default_workspace():
    """
    Default workspace in the users home directory.
    """
    workspace = os.path.join(os.path.expanduser("~"), '.codechecker')
    return workspace


def split_server_url(url):
    """
    Splits the given CodeChecker server URL into its parts.

    The format of a valid URL is:
      protocol://host:port/
    where
      * Protocol: HTTP or HTTPS
      * Host: The server's host name or IP address
      * Port: The server's port number

    As a shortcut, the following formats are also valid:
      hostname           (means: http://hostname:8001)
    """

    LOG.debug("Parsing server url '{0}'".format(url))

    protocol = 'http'
    if url.startswith('http'):
        parts = url.split('://', 1)
        protocol = parts[0]
        url = url.replace(parts[0] + '://', '')

    url = url.lstrip('/').rstrip('/')

    # A valid server_url looks like this: 'http://localhost:8001/'.
    host, port = 'localhost', 8001
    try:
        parts = url.split('/', 1)

        # Something is either a hostname, or a host:port.
        server_addr = parts[0].split(":")
        if len(server_addr) == 2:
            host, port = server_addr[0], int(server_addr[1])
        elif len(server_addr) == 1:
            host = server_addr[0]
        else:
            raise ValueError("The server's address is not in a valid "
                             "'host:port' format!")
    except:
        LOG.error("The specified server URL is invalid.")
        raise

    LOG.debug("Result: With '{0}' on server '{1}:{2}'"
              .format(protocol, host, port))

    return protocol, host, port


def create_product_url(protocol, host, port, endpoint):
    return "{0}://{1}:{2}{3}".format(protocol, host, str(port), endpoint)


def split_product_url(url):
    """
    Splits the given CodeChecker server's product-specific URL into its parts.

    The format of a valid URL is:
      protocol://host:port/ProductEndpoint
    where
      * Protocol: HTTP or HTTPS
      * Host: The server's host name or IP address
      * Port: The server's port number
      * ProductEndpoint: The product's unique endpoint folder under the server.

    As a shortcut, the following formats are also valid:
      ProductEndpoint           (means: http://localhost:8001/ProductEndpoint)
      hostname/ProductEndpoint  (means: http://hostname:8001/ProductEndpoint)
    """

    LOG.debug("Parsing product url '{0}'".format(url))

    protocol = 'http'
    if url.startswith('http'):
        parts = url.split('://', 1)
        protocol = parts[0]
        url = url.replace(parts[0] + '://', '')

    url = url.lstrip('/').rstrip('/')

    # A valid product_url looks like this: 'http://localhost:8001/Product'.
    host, port, product_name = 'localhost', 8001, 'Default'
    try:
        parts = url.split("/")

        if len(parts) == 1:
            # If only one word is given in the URL, consider it as product
            # name, but then it cannot begin with a number.
            product_name = parts[0]
            if product_name[0].isdigit():
                raise ValueError("Product name was given in URL, but it "
                                 "cannot begin with a number!")
        elif len(parts) == 2:
            # URL is at least something/product-name.
            product_name = parts[1]

            # Something is either a hostname, or a host:port.
            server_addr = parts[0].split(":")
            if len(server_addr) == 2:
                host, port = server_addr[0], int(server_addr[1])
            elif len(server_addr) == 1:
                # We consider "localhost/product" as "localhost:8001/product".
                host = server_addr[0]
            else:
                raise ValueError("The server's address is not in a valid "
                                 "'host:port' format!")
        else:
            raise ValueError("Product URL can not contain extra '/' chars.")
    except:
        LOG.error("The specified product URL is invalid.")
        raise

    LOG.debug("Result: With '{0}' on server '{1}:{2}', product '{3}'"
              .format(protocol, host, port, product_name))

    return protocol, host, port, product_name


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


def sizeof_fmt(num, suffix='B'):
    """
    Pretty print storage units.
    Source: https://stackoverflow.com/questions/1094841/
        reusable-library-to-get-human-readable-version-of-file-size
    """
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def escape_like(string, escape_char='*'):
    """Escape the string parameter used in SQL LIKE expressions."""
    return string.replace(escape_char, escape_char * 2) \
                 .replace('%', escape_char + '%') \
                 .replace('_', escape_char + '_')
