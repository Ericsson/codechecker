# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Argument handlers for the 'CodeChecker cmd components' subcommands.
"""


import sys

from codechecker_report_converter import twodim

from codechecker_common import logger
from codechecker_web.shared.env import get_user_input

from .client import setup_client
from .cmd_line import CmdLineOutputEncoder

# Needs to be set in the handler functions.
LOG = None

GEN_OTHER_COMPONENT_NAME = "Other (auto-generated)"


def init_logger(level, stream=None, logger_name='system'):
    logger.setup_logger(level, stream)
    global LOG
    LOG = logger.get_logger(logger_name)


def handle_add_component(args):
    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)

    if args.name == GEN_OTHER_COMPONENT_NAME:
        LOG.error("'%s' is a special virtual component which can not be "
                  "modified.", GEN_OTHER_COMPONENT_NAME)
        sys.exit(1)

    with open(args.component_file, 'r',
              encoding="utf-8", errors="ignore") as component_file:
        value = component_file.read().strip()

    description = args.description if 'description' in args else None

    # Check that the given source component is exists.
    source_component = client.getSourceComponents([args.name])

    if source_component:
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
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

    client = setup_client(args.product_url)
    components = client.getSourceComponents(None)

    if args.output_format == 'json':
        print(CmdLineOutputEncoder().encode(components))
    else:  # plaintext, csv
        header = ['Name', 'Value', 'Description']
        rows = []
        for res in components:
            if res.name == GEN_OTHER_COMPONENT_NAME:
                res.value = ''

            for idx, value in enumerate(res.value.split('\n')):
                name = res.name if idx == 0 else ''
                description = res.description \
                    if idx == 0 and res.description else ''
                rows.append((name, value, description))

        print(twodim.to_str(args.output_format, header, rows))


def handle_del_component(args):

    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)

    if args.name == GEN_OTHER_COMPONENT_NAME:
        LOG.error("'%s' is a special virtual component which can not be "
                  "removed.", GEN_OTHER_COMPONENT_NAME)
        sys.exit(1)

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
