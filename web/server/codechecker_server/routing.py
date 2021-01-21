# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Defines the routing rules for the CodeChecker server.
"""


import re
from urllib.parse import urlparse

from codechecker_web.shared.version import SUPPORTED_VERSIONS

# A list of top-level path elements under the webserver root
# which should not be considered as a product route.
NON_PRODUCT_ENDPOINTS = ['index.html',
                         'images',
                         'docs',
                         'live',
                         'ready']

# A list of top-level path elements in requests (such as Thrift endpoints)
# which should not be considered as a product route.
NON_PRODUCT_ENDPOINTS += ['Authentication',
                          'Products',
                          'CodeCheckerService']


# A list of top-level path elements under the webserver root which should
# be protected by authentication requirement when accessing the server.
PROTECTED_ENTRY_POINTS = ['',  # Empty string in a request is 'index.html'.
                          'index.html']


def is_valid_product_endpoint(uripart):
    """
    Returns whether or not the given URI part is to be considered a valid
    product name.
    """

    # There are some forbidden keywords.
    if uripart in NON_PRODUCT_ENDPOINTS:
        return False

    pattern = r'^[A-Za-z0-9_\-]+$'
    if not re.match(pattern, uripart):
        return False

    return True


def is_supported_version(version):
    """
    Returns whether or not the given version tag is supported by the current
    build. A version is supported if its MAJOR version is supported, and if
    its MINOR version is at most the highest minor version accepted by the
    server.

    If supported, returns the major and minor version as a tuple.
    """

    version = version.lstrip('v')
    version_parts = version.split('.')

    # We don't care if accidentally the version tag contains a revision number.
    major, minor = int(version_parts[0]), int(version_parts[1])
    if major in SUPPORTED_VERSIONS and minor <= SUPPORTED_VERSIONS[major]:
        return major, minor

    return False


def split_client_GET_request(path):
    """
    Split the given request URI to its parts relevant to the server.

    Returns the product endpoint and the "remainder" of the request path
    as a tuple of 2.
    """

    # A standard GET request from a browser looks like:
    # http://localhost:8001/[product-name]/#{request-parts}
    # where the parts are, e.g.: run=[run_id]&report=[report_id]

    parsed_path = urlparse(path).path
    split_path = parsed_path.split('/', 2)

    endpoint_part = split_path[1] if len(split_path) > 1 else None
    if endpoint_part and is_valid_product_endpoint(endpoint_part):
        remainder = split_path[2] if len(split_path) == 3 else ''
        return endpoint_part, remainder
    else:
        # The request wasn't pointing to a valid product endpoint.
        return None, parsed_path.lstrip('/')


def split_client_POST_request(path):
    """
    Split the given request URI to its parts relevant to the server.

    Returns the product endpoint, the API version and the API service endpoint
    as a tuple of 3.
    """

    # A standard POST request from an API client looks like:
    # http://localhost:8001/[product-name]/<API version>/<API service>
    # where specifying the product name is optional.

    split_path = urlparse(path).path.split('/', 3)

    endpoint_part = split_path[1]
    if is_valid_product_endpoint(split_path[1]):
        version_tag = split_path[2].lstrip('v')
        remainder = split_path[3]

        return endpoint_part, version_tag, remainder
    elif split_path[1].startswith('v'):
        # Request came through without a valid product URL endpoint to
        # possibly the main server.
        version_tag = split_path[1].lstrip('v')
        remainder = split_path[2]

        return None, version_tag, remainder

    return None, None, None


def is_protected_GET_entrypoint(path):
    """
    Returns if the given GET request's PATH enters the server through an
    entry point which is considered protected by authentication requirements.
    """
    return path in PROTECTED_ENTRY_POINTS
