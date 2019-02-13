#!/usr/bin/env python
"""
CodeChecker packager script creates a package based on the given layout config.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import errno
import json
import logging
import os
import platform
import shutil
import subprocess
import sys

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import tarfile

from distutils.spawn import find_executable

LOG = logging.getLogger('Packager')

msg_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
log_handler = logging.StreamHandler()
log_handler.setFormatter(msg_formatter)
LOG.setLevel(logging.INFO)
LOG.addHandler(log_handler)


def run_cmd(cmd, cwd=None, env=None, silent=False):
    """ Run a command. """

    LOG.debug(' '.join(cmd))
    LOG.debug(cwd)
    try:
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
        if silent:
            stdout = None
            stderr = None
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=stdout, stderr=stderr,
                                env=env)
        proc.wait()
        ret = proc.returncode
        LOG.debug(ret)
        return ret

    except TypeError as type_error:
        LOG.error('Failed to run ' + ' '.join(cmd))
        LOG.error(type_error)
        sys.exit(1)

    except OSError as os_error:
        LOG.error('Failed to run ' + ' '.join(cmd))
        LOG.error(os_error)
        sys.exit(1)


def build_ld_logger(ld_logger_path, env, arch=None, clean=True, silent=True):
    """ Build ld logger. """

    LOG.info('Building ld logger ...')
    LOG.debug(ld_logger_path)

    if clean:
        make_cmd = ['make', '-f', 'Makefile.manual', 'clean']
        ret = run_cmd(make_cmd, ld_logger_path, env, silent=silent)
        if ret:
            LOG.error('Failed to run: ' + ' '.join(make_cmd))
            return ret

    if arch == '32':
        make_cmd = ['make', '-f', 'Makefile.manual', 'pack32bit']
    elif arch == '64':
        make_cmd = ['make', '-f', 'Makefile.manual', 'pack64bit']
    else:
        make_cmd = ['make', '-f', 'Makefile.manual']

    ret = run_cmd(make_cmd, ld_logger_path, env, silent=silent)
    if ret:
        LOG.error('Failed to run: ' + ' '.join(make_cmd))
        return ret


def create_folder_layout(layout):
    """ Create package directory layout. """

    package_root = layout['root']

    LOG.info('Creating package layout')
    LOG.debug(layout)

    for key, folder in layout.items():
        if key != 'root':
            try:
                directory = os.path.join(package_root, folder)
                os.makedirs(directory)
            except OSError as os_err:
                if os_err.errno != errno.EEXIST:
                    LOG.warning(directory)
                    LOG.warning(os_err.strerror)
                    sys.exit()


def copy_tree(src, dst, skip=None):
    """ Copy file tree. """

    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        source = os.path.join(src, item)
        destination = os.path.join(dst, item)

        if skip is not None and source in skip:
            continue

        if os.path.isdir(source):
            copy_tree(source, destination, skip)
        else:
            delta = os.stat(src).st_mtime - os.stat(dst).st_mtime
            if not os.path.exists(destination) or delta > 0:
                shutil.copy2(source, destination)


def compress_to_tar(source_folder, target_folder, compress):
    """ Compress folder to tar.gz file. """

    source = source_folder.rstrip('//')
    target = target_folder.rstrip('//')
    if source == target:
        # the folder which should be compressed is
        # the same as the target folder
        return False

    target = os.path.join(target_folder, compress)

    t = tarfile.open(target, mode='w:gz')

    head, _ = os.path.split(source)

    for root, _, files in os.walk(source_folder):
        for f in files:
            cfile = os.path.join(root, f)
            rename = cfile.replace(head, '')
            LOG.debug('Compressing: %s' % rename)
            t.add(cfile, arcname=rename)
    t.close()
    return True


def get_ext_package_data(deps, dep_name):
    """ Search for a dependency in the list. """
    for dep in deps:
        if dep['name'] == dep_name:
            return dep


def build_package(repository_root, build_package_config, env=None):
    """ Package can be integrated easier to build systems if required. """

    verbose = build_package_config.get('verbose_log')
    if verbose:
        LOG.setLevel(logging.DEBUG)

    LOG.debug(env)
    LOG.debug(build_package_config)

    LOG.debug('Using build config')
    for val in build_package_config.items():
        LOG.debug(val)

    with open(build_package_config['package_layout_config'],
              'r') as pckg_layout_cfg:
        package_layout_content = pckg_layout_cfg.read()
    LOG.debug(package_layout_content)
    layout = json.loads(package_layout_content)

    LOG.debug(layout)
    package_layout = layout['static']

    output_dir = build_package_config['output_dir']
    build_dir = os.path.join(repository_root,
                             build_package_config['local_build_folder'])

    package_root = os.path.join(output_dir, 'CodeChecker')
    package_layout['root'] = package_root

    # Create package folder layout.
    create_folder_layout(package_layout)

    # Check scan-build-py (intercept).
    LOG.info('Checking source: llvm scan-build-py (intercept)')

    intercept_build_executable = find_executable('intercept-build')

    if intercept_build_executable is not None:
        LOG.info('Available')
    else:
        if platform.system() == 'Darwin':
            LOG.error('Not exists, scan-build-py (intercept) '
                      'is mandatory on OS X!')
            sys.exit(1)
        # Build ld logger because intercept is not available.
        if platform.system() == 'Linux':
            LOG.warning('Not exists, build ld logger')
            ld_logger_path = build_package_config['ld_logger_path']
            if ld_logger_path:
                ld_logger_build = os.path.join(ld_logger_path, 'build')

                clean = build_package_config.get('clean')
                ld_logger32 = build_package_config.get('ld_logger_32')
                ld_logger64 = build_package_config.get('ld_logger_64')
                rebuild = build_package_config.get('rebuild_ld_logger')\
                    or clean

                arch = None
                if ld_logger32 == ld_logger64:
                    # Build both versions.
                    pass
                elif ld_logger32:
                    arch = '32'
                elif ld_logger64:
                    arch = '64'

                if build_ld_logger(ld_logger_path, env, arch,
                                   rebuild, verbose):
                    LOG.error('Failed to build ld logger')
                    sys.exit()

                # Copy ld logger files.
                target = os.path.join(package_root,
                                      package_layout['ld_logger'])

                copy_tree(ld_logger_build, target)

                curr_dir = os.getcwd()
                os.chdir(os.path.join(package_root, package_layout['bin']))
                logger_symlink = os.path.join('../',
                                              package_layout['ld_logger'],
                                              'bin', 'ldlogger')
                os.symlink(logger_symlink, 'ldlogger')
                os.chdir(curr_dir)

            else:
                LOG.info('Skipping ld logger from package')

    # Plist to html library files.
    source = os.path.join(repository_root,
                          'vendor', 'plist_to_html', 'plist_to_html')
    target = os.path.join(package_root,
                          package_layout['lib_plist_to_html'])
    copy_tree(source, target)

    # Building Plist to html generator
    plist_to_html_path = build_package_config['plist_to_html_path']
    plist_to_html_build = os.path.join(plist_to_html_path, 'build')

    # Copy plist to html files.
    target = os.path.join(package_root,
                          package_layout['plist_to_html'])

    copy_tree(plist_to_html_build, target)

    curr_dir = os.getcwd()
    os.chdir(os.path.join(package_root, package_layout['bin']))
    plist_to_html_symlink = os.path.join('../',
                                         package_layout['plist_to_html'],
                                         'bin', 'plist-to-html')
    os.symlink(plist_to_html_symlink, 'plist-to-html')
    os.chdir(curr_dir)

    # TU collector files.
    source = os.path.join(repository_root,
                          'vendor', 'tu_collector', 'tu_collector')
    target = os.path.join(package_root,
                          package_layout['lib_tu_collector'])
    copy_tree(source, target)

    # Building TU collector.
    tu_collector_path = build_package_config['tu_collector_path']
    tu_collector_build = os.path.join(tu_collector_path, 'build')

    # Copy TU collector files.
    target = os.path.join(package_root,
                          package_layout['tu_collector'])

    copy_tree(tu_collector_build, target)

    curr_dir = os.getcwd()
    os.chdir(os.path.join(package_root, package_layout['bin']))
    tu_collector_symlink = os.path.join('../',
                                        package_layout['tu_collector'],
                                        'bin', 'tu-collector')
    os.symlink(tu_collector_symlink, 'tu-collector')
    os.chdir(curr_dir)

    # Copy Python API stubs.
    generated_api_root = os.path.join(build_dir, 'thrift')
    target = os.path.join(package_root, package_layout['gencodechecker'])

    # TODO: If we are ever to build separate CodeChecker packages, one package
    # that does not contain the 'server' command need not have every API
    # built into it.
    api_dirs = next(os.walk(generated_api_root), ([], [], []))[1]
    api_dirs.sort()
    for api_dir in api_dirs:
        api_dir = os.path.join(generated_api_root, api_dir, 'gen-py')
        LOG.debug("Copying Python Thrift API " + api_dir + " to output!")
        copy_tree(api_dir, target)

    # Copy JavaScript API stubs.
    # The web viewer needs only the latest version
    target = os.path.join(package_root, package_layout['web_client'])
    copy_tree(os.path.join(generated_api_root, api_dirs[-1], 'gen-js'),
              target)

    # CodeChecker library files.
    source = os.path.join(repository_root, 'libcodechecker')
    target = os.path.join(package_root, package_layout['libcodechecker'])
    copy_tree(source, target)

    # Documentation files.
    source = os.path.join(build_dir,
                          'gen-docs', 'html')
    target = os.path.join(package_root, package_layout['docs'])
    copy_tree(source, target)

    source = os.path.join(repository_root, 'docs', 'checker_docs')
    target = os.path.join(package_root, package_layout['checker_md_docs'])
    copy_tree(source, target)

    # config files
    LOG.debug('Copy config files')
    source = os.path.join(repository_root, 'config')
    target = os.path.join(package_root, package_layout['config'])
    copy_tree(source, target)

    # CodeChecker main scripts.
    LOG.debug('Copy main codechecker files')
    source = os.path.join(repository_root, 'bin')
    target = os.path.join(package_root, package_layout['bin'])
    target_cc = os.path.join(package_root, package_layout['cc_bin'])

    available_commands = []

    for _, _, files in os.walk(source):
        for f in files:
            if not f.endswith(".py"):
                # Non-py files use the environment to appear as python files,
                # they go into the folder in PATH as they are entrypoints.
                if f.startswith("codechecker-"):
                    commandname = f.replace("codechecker-", "")
                    available_commands.append(commandname)
                    with open(os.path.join(source, f), 'r') as file:
                        if file.readline().strip() ==\
                                "# DO_NOT_INSTALL_TO_PATH":

                            LOG.info("Registering subcommand '{0}'"
                                     .format(commandname))
                            # If the file is marked not to install, do not
                            # install it. This happens with entry points whom
                            # should not act as "lowercase" entries, but
                            # the subcommand exists as an available command.
                            continue

                    LOG.info("Registering subcommand '{0}' installed to PATH"
                             .format(commandname))
                shutil.copy2(os.path.join(source, f), target)
            else:
                # .py files are Python code that must run in a valid env.
                shutil.copy2(os.path.join(source, f), target_cc)

    available_commands.sort()
    with open(os.path.join(target_cc, 'commands.json'), 'w') as commands:
        json.dump(available_commands, commands, sort_keys=True)

    # CodeChecker web client.
    LOG.debug('Copy web client files')
    source = os.path.join(repository_root, 'www')
    target = os.path.join(package_root, package_layout['www'])

    # Copy user guide to the web directory except images which will be placed
    # to the common image directory.
    userguide_images = os.path.join(source, 'userguide', 'images')
    copy_tree(source, target, [userguide_images])
    copy_tree(userguide_images, os.path.join(target, 'images'))

    # Rename gen-docs to docs.
    target_userguide = os.path.join(package_root, package_layout['userguide'])
    shutil.move(os.path.join(target_userguide, 'gen-docs'),
                os.path.join(target_userguide, 'doc'))

    # CodeChecker db migrate.
    LOG.debug('Copy codechecker config database migration')
    source = os.path.join(repository_root, 'config_db_migrate')
    target = os.path.join(package_root,
                          package_layout['config_db_migrate'])
    copy_tree(source, target)

    LOG.debug('Copy codechecker run database migration')
    source = os.path.join(repository_root, 'db_migrate')
    target = os.path.join(package_root,
                          package_layout['run_db_migrate'])
    copy_tree(source, target)

    # License.
    license_file = os.path.join(repository_root, 'LICENSE.TXT')
    target = os.path.join(package_root)
    shutil.copy(license_file, target)

    compress = build_package_config.get('compress')
    if compress:
        LOG.info('Compressing package ...')
        compress_to_tar(package_root, output_dir, compress)
    LOG.info('Creating package finished successfully.')


if __name__ == "__main__":
    description = '''CodeChecker package creator'''

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=description)

    parser.add_argument("-l", action="store",
                        dest="package_layout_config",
                        help="Package layout configuration file.")

    parser.add_argument("-o", "--output", required=True, action="store",
                        dest="output_dir")

    parser.add_argument("-r", "--repository", required=True, action="store",
                        dest="repository",
                        help="Root path of the source repository.")

    parser.add_argument("-b", "--build-folder",
                        dest="local_build_folder",
                        default="build",
                        help="The local dependency folder under which Thrift "
                             "and documentation files have been generated.")

    parser.add_argument("--clean",
                        action="store_true",
                        dest='clean',
                        help='Clean external dependencies')

    logger_group = parser.add_argument_group('ld-logger')
    logger_group.add_argument("--ld-logger", action="store",
                              dest="ld_logger_path",
                              help="Ld logger source path.")
    logger_group.add_argument('--32', action='store_true',
                              dest="ld_logger_32",
                              help='Build for 32bit architecture.')
    logger_group.add_argument('--64', action='store_true',
                              dest="ld_logger_64",
                              help='Build for 64bit architecture.')
    logger_group.add_argument('--rebuild', action='store_true',
                              dest='rebuild_ld_logger',
                              help='Clean and rebuild logger.')

    plist_to_html_group = parser.add_argument_group('plist-to-html')
    plist_to_html_group.add_argument("--plist-to-html", action="store",
                                     dest="plist_to_html_path",
                                     help="Plist to html source path.")
    tu_collector_group = parser.add_argument_group('tu-collector')
    tu_collector_group.add_argument("--tu-collector", action="store",
                                    dest="tu_collector_path",
                                    help="TU collector source path.")

    parser.add_argument("--compress", action="store",
                        dest="compress", default=False,
                        metavar="PACKAGE.tar.gz",
                        help="Compress package to given PACKAGE.tar.gz file")

    parser.add_argument("-v", action="store_true", dest="verbose_log",
                        help='Set log level to higher verbosity.')

    args = vars(parser.parse_args())

    build_package_config = {k: args[k] for k in args if args[k] is not None}

    repository_root = build_package_config['repository']

    default_package_layout = os.path.join(repository_root,
                                          "config",
                                          "package_layout.json")
    build_package_config['package_layout_config'] = default_package_layout

    default_logger_dir = os.path.join(repository_root,
                                      'vendor',
                                      'build-logger')

    build_package_config['ld_logger_path'] = default_logger_dir

    # Set plist to html tool directory.
    default_plist_to_html_dir = os.path.join(repository_root,
                                             'vendor',
                                             'plist_to_html')

    build_package_config['plist_to_html_path'] = default_plist_to_html_dir

    # Set TU collector tool directory.
    build_package_config['tu_collector_path'] = os.path.join(repository_root,
                                                             'vendor',
                                                             'tu_collector')

    build_package(repository_root, build_package_config)
