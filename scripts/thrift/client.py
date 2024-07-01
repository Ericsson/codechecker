#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
This is a simple example how we can write our own Python client for a
CodeChecker server.

For available API functions see the .thrift files:
  https://github.com/Ericsson/codechecker/tree/master/web/api
"""

import argparse
import getpass
import re
import subprocess
import sys

from typing import Optional

try:
    # pylint: disable=no-name-in-module
    from thrift.transport import THttpClient
    from thrift.protocol import TJSONProtocol
    from thrift.Thrift import TApplicationException
except Exception:
    print("'thrift' package (https://pypi.org/project/thrift/) is not "
          "available in your environment. Please install it before you run "
          "this script again.")
    print("> pip3 install thrift==0.13.0")
    sys.exit(1)


try:
    from codechecker_api.Authentication_v6 import \
        codeCheckerAuthentication as AuthAPI_v6
    from codechecker_api.codeCheckerDBAccess_v6 import \
        codeCheckerDBAccess as ReportAPI_v6
    from codechecker_api.ProductManagement_v6 import \
        codeCheckerProductService as ProductAPI_v6
    from codechecker_api.ServerInfo_v6 import \
        serverInfoService as ServerInfoAPI_v6

    from codechecker_api_shared.ttypes import RequestFailed
except Exception:
    print("'codechecker_api' and 'codechecker_api_shared' must be available "
          "in your environment to run this script. Please install it before "
          "you run this script again:")
    print("  - https://github.com/Ericsson/codechecker/blob/master/web/api/py"
          "/codechecker_api/dist/codechecker_api.tar.gz")
    print("  - https://github.com/Ericsson/codechecker/blob/master/web/api/py"
          "/codechecker_api_shared/dist/codechecker_api_shared.tar.gz")
    sys.exit(1)


def get_client_api_version() -> str:
    """ Get client api version from the installed codechecker package. """
    p = subprocess.run([
        "pip3", "show", "codechecker_api"], stdout=subprocess.PIPE,
        check=False)
    ver = p.stdout.decode('utf-8').strip().split('\n')[1]
    res = re.search('^Version: (.*)$', ver)
    return res.group(1)


CLIENT_API = get_client_api_version()


def create_client(
    args,
    cls,
    endpoint: str,
    product_name: Optional[str] = None,
    token: Optional[str] = None
):
    """ Create a Thrift client. """
    url = f"{args.protocol}://{args.host}:{args.port}/"
    if product_name:
        url += f"{product_name}/"

    url += f"v{CLIENT_API}/{endpoint}"

    transport = THttpClient.THttpClient(url)
    protocol = TJSONProtocol.TJSONProtocol(transport)

    if token:
        transport.setCustomHeaders({
            'Cookie': f'__ccPrivilegedAccessToken={token}'})

    return cls.Client(protocol)


def main():
    """ Send multiple Thrift API requests to the server. """
    parser = argparse.ArgumentParser(
        prog="client",
        description="""
Python client to communicate with a CodeChecker server.""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    __add_arguments_to_parser(parser)
    args = parser.parse_args()

    # Get server info.
    cli_server_info = create_client(args, ServerInfoAPI_v6, "ServerInfo")
    package_version = cli_server_info.getPackageVersion()
    print(f"Package version: {package_version}\n")

    # Login to a running CodeChecker server.
    cli_auth = create_client(args, AuthAPI_v6, "Authentication")

    token = None

    auth_params = cli_auth.getAuthParameters()
    if auth_params.requiresAuthentication:
        try:
            print(f"Login '{args.username}'...")
            token = cli_auth.performLogin(
                "Username:Password", f"{args.username}:{args.password}")
            print(f"'{args.username}' successfully logged in.\n")
        except RequestFailed as ex:
            print(f"Failed to login {args.username} with the following "
                  f"exception: {ex.message}")
            sys.exit(1)
        except Exception as ex:
            print(f"Something went wrong: {ex}")
            print("Make sure your server is running.")
            sys.exit(1)

    # Get produts from the server.
    cli_product = create_client(args, ProductAPI_v6, "Products", None, token)

    product_endpoint_filter = None
    product_name_filter = None
    try:
        print("Get products...")
        products = cli_product.getProducts(
            product_endpoint_filter, product_name_filter)
        print(f"Products: {products}\n")
    except TApplicationException as ex:
        print(f"Failed to get products with the following exception: {ex}")

    # Get runs for the default product.
    cli_report = create_client(
        args, ReportAPI_v6, "CodeCheckerService", "Default", token)

    run_filter = None
    limit = 0
    offset = 0
    sort_mode = None
    try:
        print("Get runs...")
        runs = cli_report.getRunData(run_filter, limit, offset, sort_mode)
        print(f"Runs: {runs}")
    except RequestFailed as ex:
        print(f"Failed to get runs with the following exception: {ex.message}")
        sys.exit(1)


def __add_arguments_to_parser(parser):
    """ Add arguments to the the given parser. """
    parser.add_argument('--protocol',
                        dest="protocol",
                        default="http",
                        help="CodeChecker server protocol.")

    parser.add_argument('--host',
                    dest="host",
                    default="localhost",
                    help="CodeChecker server host.")

    parser.add_argument('--port',
                        dest="port",
                        default="8001",
                        help="CodeChecker server port.")

    parser.add_argument('--username',
                        dest="username",
                        default=getpass.getuser(),
                        help="The username to authenticate with.")

    parser.add_argument('--password',
                        dest="password",
                        help="Password.")

if __name__ == "__main__":
    main()
