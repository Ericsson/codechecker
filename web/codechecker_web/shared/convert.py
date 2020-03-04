# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------


import base64


def to_b64(string):
    """ encode a string to a base64 encoded string """
    return base64.b64encode(string.encode('utf-8')).decode('utf-8')


def from_b64(string_b64):
    """ decode a b46 encoded string to a string """
    return base64.b64decode(string_b64.encode('utf-8')).decode('utf-8')
