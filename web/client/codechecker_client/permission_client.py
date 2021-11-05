# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Argument handlers for the 'CodeChecker cmd permissions' subcommands.
"""

from typing import Dict

from codechecker_api.Authentication_v6.ttypes import AccessControl

from codechecker_common import logger

from .client import init_auth_client
from .cmd_line import CmdLineOutputEncoder
from .product import split_server_url

# Needs to be set in the handler functions.
LOG = None


def init_logger(level, stream=None, logger_name='system'):
    logger.setup_logger(level, stream)
    global LOG
    LOG = logger.get_logger(logger_name)


def __convert_permissions(permissions: AccessControl) -> Dict:
    """ Convert the given permissions to dictionary. """
    ret = {"user_permissions": {}, "group_permissions": {}}

    for user_name, perms in permissions.user.items():
        ret["user_permissions"][user_name] = perms

    for group_name, perms in permissions.group.items():
        ret["group_permissions"][group_name] = perms

    return ret


def handle_permissions(args):
    """
    Argument handler for the 'CodeChecker cmd permissions' subcommand
    """
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args:
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

    protocol, host, port = split_server_url(args.server_url)
    client = init_auth_client(protocol, host, port)
    access_control = client.getAccessControl()

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode({
            'version': 1,
            'global_permissions': __convert_permissions(
                access_control.globalPermissions),
            'product_permissions': {
                name: __convert_permissions(val)
                for name, val in access_control.productPermissions.items()
            },
        }))
