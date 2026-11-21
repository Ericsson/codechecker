# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import os
import yaml

from codechecker_common import logger
from codechecker_common.util import load_json

LOG = logger.get_logger('system')


def add_option(parser):
    """ Add config file option to the given parser. """
    parser.add_argument('--config',
                        dest='config_file',
                        default=os.getenv('CC_CONFIG_FILE'),
                        required=False,
                        help="R|Allow the configuration from an explicit "
                             "configuration file. The values configured in "
                             "the config file are expanded at this option's "
                             "position in the command line.\n"
                             "Defaults to the CC_CONFIG_FILE environment "
                             "variable when --config is not specified.\n"
                             "You can use any environment variable inside "
                             "this file and it will be expanded.\n"
                             "For more information see the docs: "
                             "https://github.com/Ericsson/codechecker/tree/"
                             "master/docs/config_file.md")


def get_analyze_options(cfg) -> list[str]:
    """ Get analyze related options. """
    # The config value can be 'analyze' or 'analyzer'
    # for backward compatibility.
    analyze_cfg = cfg.get("analyze", [])
    analyzer_cfg = cfg.get("analyzer", [])
    if analyze_cfg:
        if analyzer_cfg:
            LOG.warning("There is an 'analyze' and an 'analyzer' "
                        "config configuration option in the config "
                        "file. Please use the 'analyze' value to be "
                        "in sync with the subcommands.\n"
                        "Using the 'analyze' configuration.")
        return analyze_cfg

    return analyzer_cfg


def get_cmd_options(cfg, commands):
    """Get a cmd action's argument list, validating its configuration path."""
    if cfg is None:
        return []

    options = cfg
    path: list[str] = []
    for command in ['cmd', *commands]:
        if not isinstance(options, dict):
            section = '.'.join(path) or 'root'
            raise ValueError(f"Configuration section '{section}' must be "
                             "a mapping.")
        if command not in options:
            return []
        options = options[command]
        path.append(command)

    if not isinstance(options, list) or \
            not all(isinstance(option, str) for option in options):
        raise ValueError(f"Configuration section '{'.'.join(path)}' must "
                         "be a list of strings.")
    return options


def process_config_file(args, subcommand_name):
    """ Handler to get config file options. """
    if 'config_file' not in args:
        return []

    check_config_file(args)
    config_file = args.config_file
    if config_file and os.path.exists(config_file):
        if config_file.endswith(('.yaml', '.yml')):
            with open(config_file, encoding='utf-8', errors='ignore') as f:
                cfg = yaml.load(f, Loader=yaml.BaseLoader)
        else:
            cfg = load_json(config_file, default={})

        # The subcommand name is analyze but the
        # configuration section name is analyzer.
        options = None
        if subcommand_name == 'analyze':
            options = get_analyze_options(cfg)
        elif subcommand_name == 'check':
            options = [
                *get_analyze_options(cfg),
                *cfg.get("parse", [])
            ]
        elif subcommand_name == 'cmd':
            # A command group without an action should display its help.
            options = get_cmd_options(cfg, args.config_commands) \
                if 'func' in args else []
        else:
            options = cfg.get(subcommand_name, [])

        if options:
            LOG.info("Extending command line options with %s options from "
                     "'%s' file: %s", subcommand_name, args.config_file,
                     ' '.join(options))

        return options

    return []


def check_config_file(args):
    """Check if a config file is set in the arguments and if the file exists.

    returns - None if not set or the file exists or
              FileNotFoundError exception if the set config file is missing.
    """
    if 'config_file' not in args:
        return

    if 'config_file' in args and args.config_file \
            and not os.path.exists(args.config_file):
        raise FileNotFoundError(
            f"Configuration file '{args.config_file}' does not exist.")
