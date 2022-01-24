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

import sys

from typing import Optional

try:
    # pylint: disable=no-name-in-module
    from thrift.transport import THttpClient
    from thrift.protocol import TJSONProtocol
    from thrift.Thrift import TApplicationException
except:
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
except:
    print("'codechecker_api' and 'codechecker_api_shared' must be available "
          "in your environment to run this script. Please install it before "
          "you run this script again:")
    print("  - https://github.com/Ericsson/codechecker/blob/master/web/api/py/codechecker_api/dist/codechecker_api.tar.gz")
    print("  - https://github.com/Ericsson/codechecker/blob/master/web/api/py/codechecker_api_shared/dist/codechecker_api_shared.tar.gz")
    sys.exit(1)


PROTOCOL = "http"
HOST = "localhost"
PORT = 8001

USERNAME = "<myusername>"
PASSWORD = "<mypassword>"

CLIENT_API = "6.47"


def create_client(
    cls,
    endpoint: str,
    product_name: Optional[str] = None,
    token: Optional[str] = None
):
    """ Create a Thrift client. """
    url = f"{PROTOCOL}://{HOST}:{PORT}/"
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
    # Get server info.
    cli_server_info = create_client(ServerInfoAPI_v6, "ServerInfo")
    package_version = cli_server_info.getPackageVersion()
    print(f"Package version: {package_version}\n")

    # Login to a running CodeChecker server.
    cli_auth = create_client(AuthAPI_v6, "Authentication")

    token = None

    auth_params = cli_auth.getAuthParameters()
    if auth_params.requiresAuthentication:
        try:
            print(f"Login '{USERNAME}'...")
            token = cli_auth.performLogin(
                "Username:Password", f"{USERNAME}:{PASSWORD}")
            print(f"'{USERNAME}' successfully logged in.\n")
        except RequestFailed as ex:
            print(f"Failed to login {USERNAME} with the following exception: "
                f"{ex.message}")
            sys.exit(1)
        except Exception as ex:
            print(f"Something went wrong: {ex}")
            print("Make sure your server is running.")
            sys.exit(1)

    # Get produts from the server.
    cli_product = create_client(ProductAPI_v6, "Products", None, token)

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
        ReportAPI_v6, "CodeCheckerService", "Default", token)

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


if __name__ == "__main__":
    main()
