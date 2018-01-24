# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Argument handlers for the 'CodeChecker cmd product' subcommands.
"""

import base64
import sys

from ProductManagement_v6.ttypes import *

from libcodechecker.libclient.client import setup_product_client
from libcodechecker import logger
from libcodechecker.output_formatters import twodim_to_str
from libcodechecker.server.database import database_status
from libcodechecker.util import split_server_url

from cmd_line_client import CmdLineOutputEncoder

# Needs to be set in the handler functions.
LOG = None


def init_logger(level, logger_name='system'):
    logger.setup_logger(level)
    global LOG
    LOG = logger.get_logger(logger_name)


def handle_list_products(args):

    init_logger(args.verbose)

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
            name = base64.b64decode(product.displayedName_b64) \
                if product.displayedName_b64 else ''
            description = base64.b64decode(product.description_b64) \
                if product.description_b64 else ''

            if not product.accessible:
                db_status_msg = 'No access.'
            else:
                db_status = product.databaseStatus
                db_status_msg = database_status.db_status_msg.get(
                    db_status, 'Unknown database status')

            rows.append((db_status_msg,
                         product.endpoint, name, description))

        print(twodim_to_str(args.output_format, header, rows))


def handle_add_product(args):

    init_logger(args.verbose)

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
        username_b64=base64.b64encode(db_user),
        password_b64=base64.b64encode(db_pass),
        database=db_name)

    # Put together the product configuration.
    name = base64.b64encode(args.display_name) \
        if 'display_name' in args else None
    desc = base64.b64encode(args.description) \
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

    init_logger(args.verbose)

    protocol, host, port = split_server_url(args.server_url)
    client = setup_product_client(protocol, host, port)

    # Endpoints substring-match.
    products = client.getProducts(args.endpoint, None)
    products = [product for product in products
                if product.endpoint == args.endpoint]

    if len(products) == 0:
        LOG.error("The product '{0}' does not exist!"
                  .format(args.endpoint))
        return

    success = client.removeProduct(products[0].id)
    if success:
        LOG.info("Product removed.")
    else:
        LOG.error("An error occurred in product removal.")
        sys.exit(1)
