#!/usr/bin/env python
"""
CodeChecker packager script creates a package based on the given layout config.
"""
from __future__ import print_function

import argparse
import errno
import json
import logging
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import tarfile
import time

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


def create_folder_layout(path, layout):
    """ Create package directory layout. """

    package_root = layout['root']
    if not os.path.exists(package_root):
        os.makedirs(package_root)

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


def yui_compress(source, destination, yui_compress_jar):
    if not yui_compress_jar or not os.path.exists(yui_compress_jar):
        return

    # Not a javascript or css file.
    if not source.endswith('.js') and not source.endswith('.css'):
        return

    minify_cmd = ['java', '-jar', yui_compress_jar, source, '-o', destination]
    LOG.info("Compressing %s", destination)
    ret = run_cmd(minify_cmd, None, None, silent=True)
    if ret:
        LOG.error('Failed to run: ' + ' '.join(minify_cmd))
        return ret


def copy_tree(src, dst, skip=None, yui_compress_jar=None):
    """ Copy file tree. """

    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        source = os.path.join(src, item)
        destination = os.path.join(dst, item)

        if skip is not None and source in skip:
            continue

        if os.path.isdir(source):
            copy_tree(source, destination, skip, yui_compress_jar)
        else:
            delta = os.stat(src).st_mtime - os.stat(dst).st_mtime
            if not os.path.exists(destination) or delta > 0:
                if yui_compress_jar:
                    yui_compress(source, destination, yui_compress_jar)
                else:
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

    clean = build_package_config['clean']
    LOG.info('Getting external dependency projects done.')

    # Create package folder layout.
    create_folder_layout(output_dir, package_layout)

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

    npm_modules = os.path.join(repository_root, 'vendor', 'node_modules')
    yui_compress_jar = None

    minify = build_package_config.get('minify')
    if minify:
        yui_compress_jar = os.path.join(repository_root, 'vendor',
                                        'yuicompressor.jar')

        if not os.path.exists(yui_compress_jar):
            LOG.warn("YUI compressor can not be found at location %s",
                     yui_compress_jar)

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
              target,
              None,
              yui_compress_jar)

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

    # Thift js.
    thrift_root = os.path.join(npm_modules, 'thrift')
    thift_js_files = os.path.join(thrift_root, 'lib', 'js', 'src')
    target = os.path.join(package_root, package_layout['js_thrift'])
    copy_tree(thift_js_files, target, None, yui_compress_jar)

    # CodeMirror.
    codemirror_root = os.path.join(npm_modules, 'codemirror')
    target = os.path.join(package_root,
                          package_layout['web_client_codemirror'])
    copy_tree(codemirror_root, target)

    if minify:
        [yui_compress(f_, f_, yui_compress_jar) for f_ in [
            os.path.join(target, 'lib', 'codemirror.js'),
            os.path.join(target, 'lib', 'codemirror.css'),
            os.path.join(target, 'mode', 'clike', 'clike.js'),
            os.path.join(target, 'addon', 'dialog', 'dialog.js'),
            os.path.join(target, 'addon', 'dialog', 'dialog.css'),
            os.path.join(target, 'addon', 'scroll', 'annotatescrollbar.js'),
            os.path.join(target, 'addon', 'search', 'match-highlighter.js'),
            os.path.join(target, 'addon', 'search', 'search.js'),
            os.path.join(target, 'addon', 'search', 'searchcursor.js'),
            os.path.join(target, 'addon', 'edit', 'matchbrackets.js'),
            os.path.join(target, 'addon', 'fold', 'foldcode.js'),
            os.path.join(target, 'addon', 'fold', 'foldgutter.js'),
            os.path.join(target, 'addon', 'fold', 'foldgutter.css'),
            os.path.join(target, 'addon', 'fold', 'brace-fold.js'),
            os.path.join(target, 'addon', 'fold', 'xml-fold.js')
        ]]

    # Marked.
    marked_root = os.path.join(npm_modules, 'marked')
    target = os.path.join(package_root, package_layout['web_client_marked'])
    shutil.copy(os.path.join(marked_root, 'marked.min.js'), target)

    # JsPlumb.
    jsplumb_root = os.path.join(npm_modules, 'jsplumb')
    target = os.path.join(package_root, package_layout['web_client_jsplumb'])
    jsplumb = os.path.join(jsplumb_root, 'dist', 'js',
                           'jsPlumb-2.2.0-min.js')
    shutil.copy(jsplumb, target)

    # Add jQuery for JsPlumb.
    jquery_root = os.path.join(npm_modules, 'jquery')
    target = os.path.join(package_root, package_layout['web_client_jquery'])
    jquery = os.path.join(jquery_root, 'dist', 'jquery.min.js')
    shutil.copy(jquery, target)

    # config files
    LOG.debug('Copy config files')
    source = os.path.join(repository_root, 'config')
    target = os.path.join(package_root, package_layout['config'])
    copy_tree(source, target)

    version_file = os.path.join(target, 'version.json')
    LOG.debug('Extending version file: ' + version_file)

    with open(version_file) as v_file:
        version_json_data = json.load(v_file)

    git_hash = ''
    try:
        git_hash_cmd = ['git', 'rev-parse', 'HEAD']
        git_hash = subprocess.check_output(git_hash_cmd,
                                           cwd=repository_root)
        git_hash = str(git_hash.rstrip())
    except subprocess.CalledProcessError as cperr:
        LOG.warning('Failed to get last commit hash.')
        LOG.warning(str(cperr))
    except OSError as oerr:
        LOG.warning('Failed to run command:' + ' '.join(git_hash_cmd))
        LOG.warning(str(oerr))
        sys.exit(1)

    version = version_json_data['version']
    version_string = str(version['major'])
    if int(version['minor']) != 0 or int(version['revision']) != 0:
        version_string += ".{0}".format(version['minor'])
    if int(version['revision']) != 0:
        version_string += ".{0}".format(version['revision'])

    git_describe = git_describe_dirty = version_string
    try:
        # The tag only (vX.Y.Z)
        git_describe_cmd = ['git', 'describe', '--always', '--tags',
                            '--abbrev=0']
        git_describe = subprocess.check_output(git_describe_cmd,
                                               cwd=repository_root)
        git_describe = str(git_describe.rstrip())

        # The full dirty hash (vX.Y.Z-n-gabcdef0-tainted)
        git_describe_cmd = ['git', 'describe', '--always', '--tags',
                            '--dirty=-tainted']
        git_describe_dirty = subprocess.check_output(git_describe_cmd,
                                                     cwd=repository_root)
        git_describe_dirty = str(git_describe_dirty.rstrip())

        # Always replace the Git tag with the manually configured version
        # information -- but keep the "tainted" flag (if the working directory
        # differs from a commit) information visible, along with the
        # abbreviated command hash.
        # (This makes the tag compiled into the package improper, but this
        # is a design decision of the developer team!)
        git_tag = version_string
        git_tag_dirty = git_describe_dirty.replace(git_describe,
                                                   version_string)
    except subprocess.CalledProcessError as cperr:
        LOG.warning('Failed to get last commit describe.')
        LOG.warning(str(cperr))
    except OSError as oerr:
        LOG.warning('Failed to run command:' + ' '.join(git_describe_cmd))
        LOG.warning(str(oerr))
        sys.exit(1)

    version_json_data['git_hash'] = git_hash
    version_json_data['git_describe'] = {'tag': git_tag,
                                         'dirty': git_tag_dirty}

    time_now = time.strftime("%Y-%m-%dT%H:%M")
    version_json_data['package_build_date'] = time_now

    # Rewrite version config file with the extended data.
    with open(version_file, 'w') as v_file:
        v_file.write(
            json.dumps(version_json_data, sort_keys=True, indent=4))

    # Show version information on the command-line.
    LOG.debug(json.dumps(version_json_data, sort_keys=True, indent=2))
    LOG.info("This is CodeChecker v{0} ({1})"
             .format(version_string, git_hash))
    # Show the original, Git-given describe information.
    LOG.info("Built from Git tags: {0} ({1})"
             .format(git_describe, git_describe_dirty))
    # Show the touched-up version information that uses the configuration file.
    LOG.info("Baked with Git tag information merged with configured version: "
             "{0} ({1})".format(git_tag, git_tag_dirty))

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

    parser.add_argument("--minify",
                        action="store_true",
                        dest='minify',
                        help='Minify JavaScript/CSS files.')

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

    build_package(repository_root, build_package_config)
