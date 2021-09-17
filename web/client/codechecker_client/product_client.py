# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Argument handlers for the 'CodeChecker cmd product' subcommands.
"""


import sys

from codechecker_api.ProductManagement_v6.ttypes import DatabaseConnection, \
    ProductConfiguration

from codechecker_report_converter import twodim

from codechecker_common import logger

from codechecker_web.shared import database_status, convert

from .client import setup_product_client
from .cmd_line import CmdLineOutputEncoder
from .product import split_server_url

# Needs to be set in the handler functions.
LOG = None


def init_logger(level, stream=None, logger_name='system'):
    logger.setup_logger(level, stream)
    global LOG
    LOG = logger.get_logger(logger_name)


def handle_list_products(args):

    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

    protocol, host, port = split_server_url(args.server_url)
    client = setup_product_client(protocol, host, port)
    products = client.getProducts(None, None)

    if args.output_format == 'json':
        results = []
        for product in products:
            results.append({product.endpoint: product})
        print(CmdLineOutputEncoder().encode(results))
    else:  # plaintext, csv
        header = ['Database status', 'Endpoint', 'Name', 'Description']
        rows = []
        for product in products:
            name = convert.from_b64(product.displayedName_b64) \
                if product.displayedName_b64 else ''
            description = convert.from_b64(product.description_b64) \
                if product.description_b64 else ''

            if not product.accessible:
                db_status_msg = 'No access.'
            else:
                db_status = product.databaseStatus
                db_status_msg = database_status.db_status_msg.get(
                    db_status, 'Unknown database status')

            rows.append((db_status_msg,
                         product.endpoint, name, description))

        print(twodim.to_str(args.output_format, header, rows))


def handle_add_product(args):

    init_logger(args.verbose if 'verbose' in args else None)

    protocol, host, port = split_server_url(args.server_url)
    client = setup_product_client(protocol, host, port)

    # Put together the database connection's descriptor.
    if 'postgresql' in args:
        db_engine = 'postgresql'
        db_host = args.dbaddress
        db_port = args.dbport
        db_user = args.dbusername
        db_pass = args.dbpassword
        db_name = args.dbname
    else:
        db_engine = 'sqlite'
        db_host = ""
        db_port = 0
        db_user = ""
        db_pass = ""
        db_name = args.sqlite

    dbc = DatabaseConnection(
        engine=db_engine,
        host=db_host,
        port=db_port,
        username_b64=convert.to_b64(db_user),
        password_b64=convert.to_b64(db_pass),
        database=db_name)

    # Put together the product configuration.
    name = convert.to_b64(args.display_name) \
        if 'display_name' in args else None
    desc = convert.to_b64(args.description) \
        if 'description' in args else None

    prod = ProductConfiguration(
        endpoint=args.endpoint,
        displayedName_b64=name,
        description_b64=desc,
        connection=dbc)

    LOG.debug("Sending request to add product...")
    success = client.addProduct(prod)
    if success:
        LOG.info("Product added successfully.")
    else:
        LOG.error("Adding the product has failed.")
        sys.exit(1)


def handle_del_product(args):

    init_logger(args.verbose if 'verbose' in args else None)

    protocol, host, port = split_server_url(args.server_url)
    client = setup_product_client(protocol, host, port)

    # Endpoints substring-match.
    products = client.getProducts(args.endpoint, None)
    products = [product for product in products
                if product.endpoint == args.endpoint]

    if not products:
        LOG.error("The product '%s' does not exist!", args.endpoint)
        return

    success = client.removeProduct(products[0].id)
    if success:
        LOG.info("Product removed.")
    else:
        LOG.error("An error occurred in product removal.")
        sys.exit(1)
