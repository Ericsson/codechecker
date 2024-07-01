#!/usr/bin/env python3
"""
Create a wrapper for a runnable file which requires a certain virtualenv to
provide its dependencies. The wrapper implicitly uses the virtual environment,
so it does not need to activated explicitly.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from logging import getLogger, Formatter, StreamHandler, INFO, DEBUG
from os import stat, chmod, makedirs
from os.path import abspath, dirname, exists
from stat import S_IXUSR, S_IXGRP, S_IXOTH
from string import Template
import sys

LOG = getLogger('VirtualenvWrapper')

msg_formatter = Formatter('[%(levelname)s] - %(message)s')
log_handler = StreamHandler()
log_handler.setFormatter(msg_formatter)
LOG.setLevel(INFO)
LOG.addHandler(log_handler)


def add_executable_permission(path):
    """
    Extend the permissions of a file with runnable flag.
    The file owner, the group and every other user have permission
    to execute it.
    """

    current_stat = stat(path)
    chmod(path, current_stat.st_mode | S_IXUSR | S_IXGRP | S_IXOTH)


def generate_content(binary_path, virtual_environment_path):
    """
    Generate the textual representation of the wrapper script.
    """

    template_content = '''\
#!/bin/bash
source "${virtual_environment_path}/bin/activate"
exec "${binary_path}" "$$@"
'''

    template_vars = {
        'binary_path': binary_path,
        'virtual_environment_path': virtual_environment_path}

    LOG.debug('Using template:\n%s\nwith the following substitution:\n%s',
              template_content, template_vars)

    return Template(template_content).substitute(template_vars)


def create_wrapper_file(path, content):
    path = abspath(path)

    directory = dirname(path)

    if not exists(directory):
        makedirs(directory)

    with open(path, 'w', encoding="utf-8", errors="ignore") as wrapper_file:
        wrapper_file.write(content)

    add_executable_permission(path)


def create_venv_wrapper(**args):
    """
    Create a runnable file which wraps another runnable file. In addition to
    forwarding all arguments, the wrapper also activates the virtual
    environment before running the wrapped runnable file.
    """

    binary_path = args['binary']
    virtual_environment_path = args['environment']
    output_path = args['output']

    binary_path = abspath(binary_path)

    # Virtual environments have issues with being relocatable, so the virtual
    # environment is always referenced with absolute path.
    virtual_environment_path = abspath(virtual_environment_path)

    LOG.debug("Binary path used in wrapper: '%s'", binary_path)
    LOG.debug("Virtual environment path used in wrapper: '%s'",
              virtual_environment_path)

    if not exists(binary_path):
        LOG.error("Binary path '%s' does not exist!", binary_path)
        sys.exit(1)

    add_executable_permission(binary_path)

    wrapper_content = generate_content(
        binary_path, virtual_environment_path)

    create_wrapper_file(output_path, wrapper_content)


def main():
    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description="""Wrap python binaries in virtualenv. This utility can be
        used to create standalone runnable python binaries, which no longer
        require the user to explicitly activate the projects virtual
        environment.""")

    parser.add_argument('-b', '--binary',
                        required=True,
                        action='store',
                        dest='binary',
                        help="Path to the runnable file to wrap.")

    parser.add_argument('-o', '--output',
                        required=True,
                        action='store',
                        dest='output',
                        help="Path to the created wrapper file.")

    parser.add_argument('-e', '--environment',
                        required=True,
                        action='store',
                        dest='environment',
                        help="Path to the root of the virtual environment, "
                             "that is used as a wrapper.")

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        dest='verbose',
                        help="Set verbosity level.")

    args = vars(parser.parse_args())

    if 'verbose' in args and args['verbose']:
        LOG.setLevel(DEBUG)

    LOG.info('Creating virtualenv wrapper.')
    LOG.debug('Binary to wrap path argument: %s', args['binary'])
    LOG.debug('Wrapper to be created path argument: %s', args['output'])
    LOG.debug('Virtual environment path to be used argument: %s',
              args['environment'])

    create_venv_wrapper(**args)


if __name__ == "__main__":
    main()
