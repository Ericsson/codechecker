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
import shutil
import socket
import subprocess
import tempfile

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


def __strip_protocol_from_url(url):
    """
    Strip the PROTOCOL specifier from an URL string and return it, along with
    the remainder of the URL.
    """
    if '://' not in url:
        return None, url

    parts = url.split('://', 1)
    protocol = parts[0]
    url = url.replace(parts[0] + '://', '').lstrip('/').rstrip('/')

    return protocol, url


def expand_whole_protocol_and_port(protocol=None, port=None):
    """
    Calculate a full protocol and port value from the possibly None protocol
    and port values given. This method helps to default port numbers to
    connection protocols understood by CodeChecker.
    """

    proto, portnum = None, None
    if protocol:
        proto = protocol

        if protocol == 'http':
            portnum = 80
        elif protocol == 'https':
            portnum = 443
        else:
            raise ValueError("'{0}' is not a protocol understood by "
                             "CodeChecker".format(protocol))
    else:
        proto = 'http'
        portnum = 8001

    if port:
        portnum = port

    return proto, portnum


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
    protocol, url = __strip_protocol_from_url(url)

    # A valid product_url looks like this: 'http://localhost:8001/Product'.
    protocol, port = expand_whole_protocol_and_port(protocol, None)
    host = 'localhost'
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
        raise ValueError("The specified server URL is invalid.")

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
    protocol, url = __strip_protocol_from_url(url)

    # A valid product_url looks like this: 'http://localhost:8001/Product'.
    protocol, port = expand_whole_protocol_and_port(protocol, None)
    host, product_name = 'localhost', 'Default'
    try:
        parts = url.split("/")

        if len(parts) == 1:
            # If only one word is given in the URL, consider it as product
            # name, but then it must appear to be a valid product name.

            # "Only one word" URLs can be just simple host names too:
            # http://codechecker.example.com:1234 should NOT be understood as
            # the "codechecker.example.com:1234" product on "localhost:8001".
            product_name = parts[0]
            if product_name[0].isdigit() or '.' in product_name \
                    or ':' in product_name:
                raise ValueError("The given product URL is invalid. Please "
                                 "specify a full product URL.")
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
        raise ValueError("The specified product URL is invalid.")

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


def get_line(file_name, line_no):
    """
    Return the given line from the file. If line_no is larger than the number
    of lines in the file then empty string returns.
    If the file can't be opened for read, the function also returns empty
    string.
    """
    try:
        with open(file_name) as f:
            for line in f:
                line_no -= 1
                if line_no == 0:
                    return line
            return ''
    except IOError:
        return ''


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
