#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Generate a new CodeChecker subcommand and the structure needed for it in the
working directory.
"""


import os
import sys


def main():

    try:
        command_name = sys.argv[1]
    except IndexError:
        print("Please provide the command's name (such as 'log')")
        sys.exit(1)

    current_dir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, '..'))

    bin_dir = os.path.join(parent_dir, 'bin')
    lib_dir = os.path.join(parent_dir, 'libcodechecker')
    handler_dir = os.path.join(lib_dir, 'libhandlers')

    if os.path.exists(os.path.join(bin_dir, 'codechecker-' + command_name)) \
            or os.path.exists(os.path.join(lib_dir, command_name)) \
            or os.path.exists(os.path.join(handler_dir, command_name + '.py')):
        print("This command already exists, refusing to create!")
        sys.exit(1)

    resource_dir = os.path.join(current_dir, 'resources')

    entryfile = os.path.join(bin_dir, 'codechecker-' + command_name)
    print("Creating new entrypoint in '" + entryfile + "'")
    with open(os.path.join(resource_dir, 'entrypoint_template.py'),
              encoding="utf-8", errors="ignore") as template:
        with open(entryfile, 'w', encoding="utf-8", errors="ignore") as entry:
            contents = template.read()
            contents = contents.replace("$COMMAND$", command_name)
            entry.write(contents)

    os.chmod(entryfile, 0o755)

    lib_name = command_name
    if '-' in command_name:
        print("- (hyphen) found in command name.")
        print("Replacing with _ (underscore) to ensure compatibility with ")
        print("Python coding standards in the library folder.")
        lib_name = command_name.replace('-', '_')

    print("Creating library package")
    os.makedirs(os.path.join(lib_dir, lib_name))
    with open(os.path.join(lib_dir, lib_name, '__init__.py'), 'w',
              encoding="utf-8", errors="ignore") as init:
        # Write licensing information to init of module
        s = "# --------------------------------------------------------------"\
            "---------------""""
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------"""\
            "----\n"

        init.write(s)

    handler_file = os.path.join(handler_dir, lib_name + '.py')
    print("Creating subcommand definition in '" + handler_file + "'")
    with open(os.path.join(resource_dir, 'command_template.py'),
              encoding="utf-8", errors="ignore") as template:
        with open(handler_file, 'w',
                  encoding="utf-8", errors="ignore") as libfile:
            contents = template.read()
            contents = contents.replace("$COMMAND$", command_name)
            libfile.write(contents)

    print("\n")
    print("Subcommand created successfully")
    print("-------------------------------")
    print("Please see the file ")
    print("'" + handler_file + "'")
    print("to add your subcommand's argument list, detailed help,")
    print("and to write the main() of the subcommand.")
    print("")
    print("Please rebuild CodeChecker to make sure your command is available.")
    print("Also please make sure you add the following paths to version "
          "control:")
    print("  * " + entryfile)
    print("  * " + handler_file)
    print("  * " + os.path.join(lib_dir, lib_name))


if __name__ == "__main__":
    main()
