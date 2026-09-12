# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import os
import shlex
import yaml

from codechecker_common import logger
from codechecker_common.util import load_json

LOG = logger.get_logger('system')


def add_option(parser):
    """ Add config file option to the given parser. """
    parser.add_argument('--config',
                        dest='config_file',
                        required=False,
                        help="R|Allow the configuration from an explicit "
                             "configuration file. The values configured in "
                             "the config file will overwrite the values set "
                             "in the command line.\n"
                             "You can use any environment variable inside "
                             "this file and it will be expaneded.\n"
                             "For more information see the docs: "
                             "https://github.com/Ericsson/codechecker/tree/"
                             "master/docs/config_file.md")


class ConfigFileTokenizeError(Exception):
    """
    Raised when a config file entry cannot be split into command line
    arguments, e.g. because of an unterminated quote.
    """


def _tokenize_entry(entry, config_file, section):
    """
    Split a single config file entry into command line arguments.

    YAML and JSON entries are both single strings, but a string may hold more
    than one argument (e.g. '--analyzers clangsa clang-tidy'). Splitting is
    done with shlex so that quoting, escapes and spaces inside quoted values
    behave like they do on the command line. Comments are disabled: a '#'' in
    behave like they do on the command line. Comments are disabled: a '#' in
    """
    if not isinstance(entry, str):
        raise ConfigFileTokenizeError(
            f"Invalid entry in '{config_file}' under '{section}': expected a "
            f"string, got {type(entry).__name__}.")

    try:
        return shlex.split(entry, comments=False, posix=True)
    except ValueError as ex:
        raise ConfigFileTokenizeError(
            f"Invalid quoting in '{config_file}' under '{section}': "
            f"{ex}\n"
            f"  entry: {entry!r}\n"
            f"If a value contains a space, quote it, e.g. "
            f"'- --trim-path-prefix \"/tmp/my project\"'.") from ex


def _expand_section_options(entries, config_file, section) -> list[str]:
    """
    Tokenize every entry of a config file section and flatten the results.

    One list item may therefore produce several command line arguments.
    Entries that produce more than one argument are logged, because a config
    file written for the previous behavior (where one entry was always exactly
    one argument) can silently change meaning.
    """
    options = []
    for entry in entries:
        tokens = _tokenize_entry(entry, config_file, section)
        if len(tokens) > 1:
            LOG.info("Config file entry %r in '%s' under '%s' was split into "
                     "multiple command line arguments: %s",
                     entry, config_file, section, tokens)
        options.extend(tokens)
    return options


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


def process_config_file(args, subcommand_name):
    """ Handler to get config file options. """
    if 'config_file' not in args:
        return {}

    config_file = args.config_file
    if config_file and os.path.exists(config_file):
        if config_file.endswith(('.yaml', '.yml')):
            with open(config_file, encoding='utf-8', errors='ignore') as f:
                cfg = yaml.load(f, Loader=yaml.BaseLoader)
        else:
            cfg = load_json(config_file, default={})

        is_yaml = config_file.endswith(('.yaml', '.yml'))

        # The subcommand name is analyze but the
        # configuration section name is analyzer.
        if subcommand_name == 'analyze':
            sections = [('analyze', get_analyze_options(cfg))]
        elif subcommand_name == 'check':
            sections = [
                ('analyze', get_analyze_options(cfg)),
                ('parse', cfg.get("parse", [])),
            ]
        else:
            sections = [(subcommand_name, cfg.get(subcommand_name, []))]

        options = []
        for section, entries in sections:
            if not entries:
                continue
            # JSON has always been one-entry-per-argument; only YAML entries
            # may hold several arguments in a single item.
            if is_yaml:
                options.extend(
                    _expand_section_options(entries, config_file, section))
            else:
                options.extend(entries)

        if options:
            LOG.info("Extending command line options with %s options from "
                     "'%s' file: %s", subcommand_name, args.config_file,
                     ' '.join(options))

        return options

    return {}


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
