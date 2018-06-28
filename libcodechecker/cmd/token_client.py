# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Argument handlers for the 'CodeChecker cmd token' subcommands.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from libcodechecker import logger
from libcodechecker.libclient.client import setup_auth_client
from libcodechecker.output_formatters import twodim_to_str
from libcodechecker.util import CmdLineOutputEncoder, split_server_url

# Needs to be set in the handler functions.
LOG = None


def init_logger(level, logger_name='system'):
    logger.setup_logger(level)
    global LOG
    LOG = logger.get_logger(logger_name)


def handle_add_token(args):
    """
    Creates a new personal access token for the logged in user based on the
    arguments.
    """
    init_logger(args.verbose if 'verbose' in args else None)

    protocol, host, port = split_server_url(args.server_url)
    client, _ = setup_auth_client(protocol, host, port)

    description = args.description if 'description' in args else None
    session = client.newToken(description)

    print("The following access token has been generated for your account: " +
          session.token)


def handle_list_tokens(args):
    """
    List personal access tokens of the currently logged in user.
    """
    init_logger(args.verbose if 'verbose' in args else None)

    protocol, host, port = split_server_url(args.server_url)
    client, curr_token = setup_auth_client(protocol, host, port)
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

        print(twodim_to_str(args.output_format, header, rows))


def handle_del_token(args):
    """
    Removes a personal access token of the currently logged in user.
    """
    init_logger(args.verbose if 'verbose' in args else None)

    protocol, host, port = split_server_url(args.server_url)
    client, _ = setup_auth_client(protocol, host, port)

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
