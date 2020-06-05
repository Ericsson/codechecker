# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Product module.
"""


from codechecker_common.logger import get_logger

LOG = get_logger('system')


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

    if protocol:
        if protocol == 'http':
            portnum = 80
        elif protocol == 'https':
            portnum = 443
        else:
            raise ValueError("'{0}' is not a protocol understood by "
                             "CodeChecker".format(protocol))
    else:
        protocol = 'http'
        portnum = 8001

    if port:
        portnum = port

    return protocol, portnum


def understand_server_addr(server_addr):
    """
    Attempts to understand the given server address and fetch the hostname
    or host address and optionally the port from it.
    """
    parts = server_addr.split(':')

    if len(parts) == 2:
        return parts[0], int(parts[1])
    if len(parts) == 1:
        return parts[0], None

    # Multiple ':'s found in the URL, which means it could be an
    # IPv6 address, if it is in the right format.
    if parts[0].startswith('['):
        if parts[-1].endswith(']'):
            # The address was [::1], there is no port number.
            return ':'.join(parts), None
        if parts[-2].endswith(']'):
            # The address was such as [::1]:1234.
            return ':'.join(parts[:-1]), int(parts[-1])

    raise ValueError("The server's address is not in a valid "
                     "'host:port' or '[host]:port' format!")


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

    LOG.debug("Parsing server url '%s'", url)
    protocol, url = __strip_protocol_from_url(url)

    # A valid product_url looks like this: 'http://localhost:8001/Product'.
    protocol, port = expand_whole_protocol_and_port(protocol, None)
    host = 'localhost'
    try:
        parts = url.split('/', 1)

        # Something is either a hostname, or a host:port.
        server_addr = parts[0]
        host, maybe_port = understand_server_addr(server_addr)
        if maybe_port:
            port = maybe_port
    except Exception:
        raise ValueError("The specified server URL is invalid.")

    LOG.debug("Result: With '%s' on server '%s:%s'",
              protocol, host, port)

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

    LOG.debug("Parsing product url '%s'", url)
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
            server_addr = parts[0]
            host, maybe_port = understand_server_addr(server_addr)
            if maybe_port:
                port = maybe_port
        else:
            raise ValueError("Product URL can not contain extra '/' chars.")
    except Exception:
        raise ValueError("The specified product URL is invalid.")

    LOG.debug("Result: With '%s' on server '%s:%s', product '%s'",
              protocol, host, port, product_name)

    return protocol, host, port, product_name
