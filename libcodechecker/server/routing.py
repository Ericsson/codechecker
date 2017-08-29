# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Defines the routing rules for the CodeChecker server.
"""

import re
import urlparse

# A list of top-level path elements under the webserver root
# which should not be considered as a product route.
NON_PRODUCT_ENDPOINTS = ['products.html',
                         'index.html',
                         'fonts',
                         'images',
                         'scripts',
                         'style'
                         ]

# A list of top-level path elements in requests (such as Thrift endpoints)
# which should not be considered as a product route.
NON_PRODUCT_ENDPOINTS += ['Authentication',
                          'Products',
                          'CodeCheckerService'
                          ]


def is_valid_product_endpoint(uripart):
    """
    Returns whether or not the given URI part is to be considered a valid
    product name.
    """

    # There are some forbidden keywords.
    if uripart in NON_PRODUCT_ENDPOINTS:
        return False

    # Like programming variables: begin with letter and then letters, numbers,
    # underscores.
    pattern = r'^[A-Za-z][A-Za-z0-9_]*$'
    if not re.match(pattern, uripart):
        return False

    return True


def get_product_name(path):
    """
    Get product name from the request's URI.
    """

    # A standard request from a browser looks like:
    # http://localhost:8001/[product-name]/#{request-parts}
    # where the parts are, e.g.: run=[run_id]&report=[report_id]
    #
    # Rewrite the "product-name" so that the web-server deploys the
    # viewer client from the www/ folder.

    # The split array looks like ['', 'product-name', ...].
    first_part = urlparse.urlparse(path).path.split('/', 2)[1]
    return first_part if is_valid_product_endpoint(first_part) else None
