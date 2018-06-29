# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
The libcodechecker.libhandlers package contains the individual subcommands that
can be used in CodeChecker. Each module in itself defines its subcommand's
argument list, help text, and the invocation.

This file contains basic methods to handle dynamic subcommand loading.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import imp


def load_module(name):
    """
    Load the subcommand module with the given name from the package.
    This method returns the Python module object.
    """
    # Even though command verbs and nouns are joined by a
    # hyphen, the Python files contain underscores.
    name = name.replace('-', '_')

    # Load the 'libcodechecker' module and acquire its path.
    cc_file, cc_path, cc_descr = imp.find_module("libcodechecker")
    libcc_path = imp.load_module("libcodechecker",
                                 cc_file, cc_path, cc_descr).__path__

    # Load the 'libcodechecker.libhandlers' module and acquire its path.
    handler_file, handler_path, handler_descr = \
        imp.find_module("libhandlers", libcc_path)
    libhandlers_path = imp.load_module("libhandlers",
                                       handler_file,
                                       handler_path,
                                       handler_descr).__path__

    # Load the module named as the argument.
    command_file, command_path, command_descr = \
        imp.find_module(name, libhandlers_path)
    return imp.load_module(name, command_file, command_path, command_descr)


def add_subcommand(subparsers, subcommand):
    """
    Load the subcommand module and then add the subcommand to the available
    subcommands in the given subparsers collection.

    subparsers has to be the return value of the add_parsers() method on an
    argparse.ArgumentParser.
    """

    command_module = load_module(subcommand)

    # Now that the module is loaded, construct an ArgumentParser for it.
    sc_parser = subparsers.add_parser(
        subcommand, **command_module.get_argparser_ctor_args())

    # Run the method which adds the arguments to the subcommand's handler.
    command_module.add_arguments_to_parser(sc_parser)
