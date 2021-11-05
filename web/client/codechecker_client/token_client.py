# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Argument handlers for the 'CodeChecker cmd token' subcommands.
"""

from codechecker_report_converter import twodim

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


def handle_add_token(args):
    """
    Creates a new personal access token for the logged in user based on the
    arguments.
    """
    init_logger(args.verbose if 'verbose' in args else None)

    protocol, host, port = split_server_url(args.server_url)
    client = init_auth_client(protocol, host, port)

    description = args.description if 'description' in args else None
    session = client.newToken(description)

    print("The following access token has been generated for your account: " +
          session.token)


def handle_list_tokens(args):
    """
    List personal access tokens of the currently logged in user.
    """
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

    protocol, host, port = split_server_url(args.server_url)
    client = init_auth_client(protocol, host, port)
    tokens = client.getTokens()

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(tokens))
    else:  # plaintext, csv
        header = ['Token', 'Description', 'Last access']
        rows = []
        for res in tokens:
            rows.append((res.token,
                         res.description if res.description else '',
                         res.lastAccess))

        print(twodim.to_str(args.output_format, header, rows))


def handle_del_token(args):
    """
    Removes a personal access token of the currently logged in user.
    """
    init_logger(args.verbose if 'verbose' in args else None)

    protocol, host, port = split_server_url(args.server_url)
    client = init_auth_client(protocol, host, port)

    token = args.token
    try:
        success = client.removeToken(token)

        if success:
            print("'" + token + "' has been successfully removed.")
        else:
            print("Error: '" + token + "' can not be removed.")
    except Exception as ex:
        LOG.error("Failed to remove the token!")
        LOG.error(ex)
