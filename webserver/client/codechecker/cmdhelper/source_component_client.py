# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Argument handlers for the 'CodeChecker cmd components' subcommands.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import sys

from ..client.client import setup_client

from libcodechecker import logger
from libcodechecker.output_formatters import twodim_to_str
from libcodechecker.util import get_user_input, CmdLineOutputEncoder

# Needs to be set in the handler functions.
LOG = None


def init_logger(level, logger_name='system'):
    logger.setup_logger(level)
    global LOG
    LOG = logger.get_logger(logger_name)


def check_unicode_string(check_str, var_name):
    try:
        check_str.decode()
    except UnicodeDecodeError as ex:
        LOG.error("%s contains unicode characters which is not "
                  "supported by this client!", var_name)
        LOG.debug(ex)
        sys.exit(1)


def handle_add_component(args):
    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)

    with open(args.component_file, 'r') as component_file:
        value = component_file.read().strip()

    description = args.description if 'description' in args else None

    check_unicode_string(args.name, "Component name")

    if description:
        check_unicode_string(args.description, "Component description")

    # Check that the given source component is exists.
    source_component = client.getSourceComponents([args.name])

    if len(source_component):
        LOG.info("The source component '%s' already exist!", args.name)

        question = 'Do you want to update? Y(es)/n(o) '
        if not get_user_input(question):
            LOG.info("No source component update was done.")
            sys.exit(0)

    success = client.addSourceComponent(args.name, value, description)
    if success:
        LOG.info("Source component added.")
    else:
        LOG.error("An error occurred when adding source component.")
        sys.exit(1)


def handle_list_components(args):
    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)
    components = client.getSourceComponents(None)

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(components))
    else:  # plaintext, csv
        header = ['Name', 'Value', 'Description']
        rows = []
        for res in components:
            for idx, value in enumerate(res.value.split('\n')):
                name = res.name if idx == 0 else ''
                description = res.description \
                    if idx == 0 and res.description else ''
                rows.append((name, value, description))

        print(twodim_to_str(args.output_format, header, rows))


def handle_del_component(args):

    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)

    # Check that the given source component is exists.
    source_component = client.getSourceComponents([args.name])

    if not source_component:
        LOG.error("The source component '%s' does not exist!", args.name)
        sys.exit(1)

    success = client.removeSourceComponent(args.name)
    if success:
        LOG.info("Source component removed.")
    else:
        LOG.error("An error occurred in source component removal.")
        sys.exit(1)
