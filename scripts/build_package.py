#!/usr/bin/env python
"""
CodeChecker packager script creates a package based on the given layout config.
"""
from __future__ import print_function

import argparse
import errno
import json
import logging
import ntpath
import re
import platform
import os
import shlex
import shutil
import subprocess
import sys

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import tarfile
import tempfile
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

    if arch is None:
        make_cmd = ['make', '-f', 'Makefile.manual']
    elif arch == '32':
        make_cmd = ['make', '-f', 'Makefile.manual', 'pack32bit']
    elif arch == '64':
        make_cmd = ['make', '-f', 'Makefile.manual', 'pack64bit']

    ret = run_cmd(make_cmd, ld_logger_path, env, silent=silent)
    if ret:
        LOG.error('Failed to run: ' + ' '.join(make_cmd))
        return ret


def create_folder_layout(path, layout):
    """ Create package directory layout. """

    package_root = layout['root']
    if os.path.exists(path):
        LOG.info('Removing previous package')
        if os.path.exists(package_root):
            shutil.rmtree(package_root)
    else:
        os.makedirs(path)

    LOG.info('Creating package layout')
    LOG.debug(layout)

    os.makedirs(package_root)
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


def copy_tree(src, dst):
    """ Copy file tree. """

    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        source = os.path.join(src, item)
        destination = os.path.join(dst, item)
        if os.path.isdir(source):
            copy_tree(source, destination)
        else:
            delta = os.stat(src).st_mtime - os.stat(dst).st_mtime
            if not os.path.exists(destination) or delta > 0:
                shutil.copy2(source, destination)


def handle_external_file(dep, clean, env, verbose):
    """
    Download (and if needed, extract) files from the given url.
    Currently supports handling of files with the following extensions:
      .tar.gz, .js, .css
    """
    supported_exts = {
        'compressed': ['.tar.gz'],
        'uncompressed': ['.js', '.css']
    }

    source_package = dep['source_package']
    directory = dep['directory']
    if clean and os.path.exists(directory):
        LOG.debug('Removing directory ' + directory)
        shutil.rmtree(directory)
    else:
        if os.path.exists(directory):
            return

    os.makedirs(directory)
    download_cmd = []
    download_cmd.extend(shlex.split(source_package['download_cmd']))
    file_url = source_package['url']
    download_cmd.append(file_url)

    option = source_package['option']
    download_cmd.append(option)

    file_name = source_package['name']
    download_cmd.append(file_name)

    LOG.info('Downloading ...')
    if run_cmd(download_cmd, directory, env, verbose):
        LOG.error('Failed to get dependency')
        sys.exit(1)

    url_data = urlparse.urlparse(file_url)
    head, file_name = ntpath.split(url_data.path)

    head, file_ext = os.path.splitext(file_name)
    if file_ext == '.gz' and head.endswith('.tar'):
        file_ext = '.tar.gz'

    if file_ext in supported_exts['compressed']:
        if file_ext == '.tar.gz':
            file_name = os.path.join(directory, file_name)
            with tarfile.open(file_name) as tar:
                tar.extractall(directory)
            os.remove(file_name)
        else:
            LOG.error('Unsupported file type')
    elif file_ext in supported_exts['uncompressed']:
        pass
    else:
        LOG.error('Unsupported file type')


font_user_agents = {
    'default': '""',
    'eot': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)',
    'woff': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:27.0) '
            'Gecko/20100101 Firefox/27.0',
    'woff2': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) '
             'Gecko/20100101 Firefox/40.0',
    'svg': 'Mozilla/4.0 (iPad; CPU OS 4_0_1 like Mac OS X) AppleWebKit/534.46'
           '(KHTML, like Gecko) Version/4.1 Mobile/9A405 Safari/7534.48.3',
    'ttf': 'Mozilla/5.0 (Linux; Android 4.3; HTCONE Build/JSS15J) '
           'AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 '
           'Mobile Safari/534.30'}


def handle_external_repository(dep, clean, env, verbose):
    """ Download external repository. """
    repository = dep['repository']
    directory = dep['directory']
    if clean and os.path.exists(directory):
        LOG.debug('Removing directory ' + directory)
        shutil.rmtree(directory)
    else:
        if os.path.exists(directory):
            return

    if repository['type'] == 'git':
        directory = dep['directory']
        if clean and os.path.exists(directory):
            LOG.debug('Removing directory ' + directory)
            shutil.rmtree(directory)
        else:
            if os.path.exists(directory):
                return

        git_cmd = ['git', 'clone', '--depth', '1', '--single-branch']

        git_tag = repository.get('git_tag')
        if git_tag:
            git_cmd.append('-b')
            git_cmd.append(git_tag)
        git_cmd.append(repository.get('url'))
        git_cmd.append(directory)

        dir_name, tail = ntpath.split(directory)
        LOG.info('Downloading ...')
        if run_cmd(git_cmd, dir_name, env=env, silent=verbose):
            LOG.error('Failed to get dependency')
            sys.exit(1)
    elif repository['type'] == 'font_import':
        # Download the font information from the given CSS file
        source = repository.get('url')
        font = repository.get('font')

        if not os.path.exists(directory):
            os.makedirs(directory)

        if source:
            tmp = tempfile.mkdtemp()
            LOG.debug("Downloading font files " + source + " to " + tmp)
            for fformat, agent in font_user_agents.iteritems():
                command = ['curl', '-sSfLk',
                           '-A', agent,
                           '--get', source,
                           '-o', os.path.join(tmp,
                                              fformat + '.css')]
                if run_cmd(command, env=env):
                    LOG.warning("Failed to download font CSS for {0} "
                                "(format {1})".format(source, fformat))
                    continue

                LOG.debug("Font format " + fformat + " downloaded.")

            localdefs = []
            urls = []
            for _, _, files in os.walk(tmp):
                for fontcss in files:
                    if fontcss == "default.css":
                        continue

                    font_type = fontcss.replace(".css", "")
                    fontcss = os.path.join(tmp, fontcss)
                    LOG.debug("Retrieving font for " + font + "(" +
                              os.path.basename(fontcss) + ")")
                    with open(fontcss, 'r') as input:
                        css = input.read()

                    for local_name in re.findall(r'local\(([\S ]+?)\)', css):
                        if local_name not in localdefs:
                            localdefs.append("local(" + local_name + ")")

                    src = re.search(r'url\(([\S]+)\)( format\(([\S]+)\))?',
                                    css)
                    command = ['curl', '-sSfLk',
                               '-A',
                               font_user_agents[font_type],
                               '--get', src.group(1),
                               '-o', os.path.join(tmp,
                                                  font + '.' + font_type)]
                    if run_cmd(command, env=env):
                        LOG.warning("Couldn't download font FILE for "
                                    "{0}.{1}".format(font, font_type))
                        continue

                    if font_type == 'svg':
                        # SVG fonts need a HTTP anchor to work,
                        # i.e. Arial.svg#Arial, not just Arial.svg

                        url_parsed = urlparse.urlparse(src.group(1))
                        suffix = font_type + "#" + url_parsed.fragment
                    else:
                        suffix = font_type

                    urls.append("url('" +
                                os.path.join("..", "fonts",
                                             font + '.' + suffix) +
                                "')" + src.group(2) if src.group(2) else '')

                    # Export the downloaded files
                    basename = font + '.' + font_type
                    shutil.copy(os.path.join(tmp, basename),
                                os.path.join(directory, basename))

            # Export "fixed" font information
            localdefs = list(set(localdefs))
            with open(os.path.join(tmp, "default.css"), 'r') as cssfile:
                css = re.sub(r'(src:.*;)', "{SRCLINE}", cssfile.read())
                css = css.replace("{SRCLINE}",
                                  "src: " + ','.join(localdefs + urls)
                                               .rstrip(',')
                                               .replace(',', ',\n       ') +
                                  ";")

                with open(os.path.join(directory, "generated_fonts.css"),
                          'w') as export:
                    export.write(css)

            shutil.rmtree(tmp)
        else:
            LOG.error('Font repository URL was not given!')
    else:
        LOG.error('Unsupported repository type')


def handle_vendor_record(dep, clean, env, verbose):
    """ Handle external project dependencies."""

    LOG.info('Checking source: ' + dep['name'])

    if dep.get('source_package') is None and dep.get('repository') is None:
        LOG.error('Missing download for source dependency: ' + dep['name'])
        sys.exit(1)

    if dep.get('source_package'):
        handle_external_file(dep, clean, env, verbose)

    if dep.get('repository'):
        handle_external_repository(dep, clean, env, verbose)

    LOG.info('Done.')


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

    head, tail = os.path.split(source)

    for root, dirs, files in os.walk(source_folder):
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

    # Get external dependencies.
    vendor_dir = os.path.join(repository_root, 'vendor')
    vendor_proj_config = os.path.join(repository_root, 'vendor_projects.json')
    LOG.debug(vendor_proj_config)
    with open(vendor_proj_config, 'r') as vendor_cfg:
        vendor_proj_config = vendor_cfg.read()
        vendor_projs = json.loads(vendor_proj_config)

    clean = build_package_config['clean']
    for dep in vendor_projs:
        dep['directory'] = os.path.join(repository_root, dep['directory'])
        handle_vendor_record(dep, clean, env, verbose)

    vendor_projects = {dep['name']: dep for dep in vendor_projs}

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

    generated_py_files = os.path.join(build_dir, 'gen-py')
    generated_js_files = os.path.join(build_dir, 'gen-js')

    target = os.path.join(package_root, package_layout['gencodechecker'])
    copy_tree(generated_py_files, target)

    target = os.path.join(package_root, package_layout['web_client'])
    copy_tree(generated_js_files, target)

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
    thrift_dep = vendor_projects['thrift']
    thrift_root = os.path.join(repository_root, thrift_dep.get('directory'))
    thift_js_files = os.path.join(thrift_root, 'lib', 'js', 'src')
    target = os.path.join(package_root, package_layout['js_thrift'])
    copy_tree(thift_js_files, target)

    # CodeMirror.
    codemirror_dep = vendor_projects['codemirror']
    codemirror_root = os.path.join(repository_root,
                                   codemirror_dep.get('directory'))
    target = os.path.join(package_root,
                          package_layout['web_client_codemirror'])
    copy_tree(codemirror_root, target)

    # HighlightJs.
    highlightjs_dep = vendor_projects['highlightjs']
    highlightjs_root = os.path.join(repository_root,
                                    highlightjs_dep.get('directory'))
    target = os.path.join(package_root,
                          package_layout['web_client_highlightjs'])
    copy_tree(highlightjs_root, target)

    # HighlightJs_css.
    highlightjs_css_dep = vendor_projects['highlightjs_css']
    highlightjs_css_root = os.path.join(repository_root,
                                        highlightjs_css_dep.get('directory'))
    target = os.path.join(package_root,
                          package_layout['web_client_highlightjs'])
    target = os.path.join(target, 'css')
    copy_tree(highlightjs_css_root, target)

    # Dojo.
    dojo_dep = vendor_projects['dojotoolkit']
    file_url = dojo_dep['source_package']['url']
    url_data = urlparse.urlparse(file_url)
    head, file_name = ntpath.split(url_data.path)
    head, tail = file_name.split('.tar.gz')

    dojo_root = os.path.join(repository_root, dojo_dep.get('directory'))
    dojo_root = os.path.join(dojo_root, head)
    target = os.path.join(package_root, package_layout['web_client_dojo'])
    copy_tree(dojo_root, target)

    # Marked.
    marked_dep = vendor_projects['marked']
    marked_root = os.path.join(repository_root, marked_dep.get('directory'))
    target = os.path.join(package_root, package_layout['web_client_marked'])
    shutil.copy(os.path.join(marked_root, 'marked.min.js'), target)

    # JsPlumb.
    jsplumb_dep = vendor_projects['jsplumb']
    jsplumb_root = os.path.join(repository_root, jsplumb_dep.get('directory'))
    target = os.path.join(package_root, package_layout['web_client_jsplumb'])
    jsplumb = os.path.join(jsplumb_root, 'dist', 'js',
                           'jquery.jsPlumb-1.7.6-min.js')
    shutil.copy(jsplumb, target)

    # Add jQuery for JsPlumb.
    target = os.path.join(target, 'external')
    if not os.path.exists(target):
        os.mkdir(target)
    jquery = os.path.join(jsplumb_root, 'external',
                          'jquery-1.9.0-min.js')
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

    git_describe = '.'.join(version_json_data['version'].values())
    git_describe_dirty = git_describe
    try:
        # The full dirty hash (vX.Y.Z-n-gabcdef0-tainted)

        git_describe_cmd = ['git', 'describe', '--always', '--tags',
                            '--dirty=-tainted']
        git_describe_dirty = subprocess.check_output(git_describe_cmd,
                                                     cwd=repository_root)
        git_describe_dirty = str(git_describe_dirty.rstrip())

        # The tag only (vX.Y.Z)
        git_describe_cmd = ['git', 'describe', '--always', '--tags',
                            '--abbrev=0']
        git_describe = subprocess.check_output(git_describe_cmd,
                                               cwd=repository_root)
        git_describe = str(git_describe.rstrip())
    except subprocess.CalledProcessError as cperr:
        LOG.warning('Failed to get last commit describe.')
        LOG.warning(str(cperr))
    except OSError as oerr:
        LOG.warning('Failed to run command:' + ' '.join(git_describe_cmd))
        LOG.warning(str(oerr))
        sys.exit(1)

    version_json_data['git_hash'] = git_hash
    version_json_data['git_describe'] = {'tag': git_describe,
                                         'dirty': git_describe_dirty}

    time_now = time.strftime("%Y-%m-%dT%H:%M")
    version_json_data['package_build_date'] = time_now

    # Rewrite version config file with the extended data.
    with open(version_file, 'w') as v_file:
        v_file.write(json.dumps(version_json_data, sort_keys=True, indent=4))

    # CodeChecker web client.
    LOG.debug('Copy web client files')
    source = os.path.join(repository_root, 'www')
    target = os.path.join(package_root, package_layout['www'])
    copy_tree(source, target)

    # Copy font files.
    for _, dep in vendor_projects.iteritems():
        if 'repository' not in dep:
            continue
        if dep['repository']['type'] != "font_import":
            continue

        root = os.path.join(repository_root,
                            dep.get('directory'))
        target = os.path.join(package_root,
                              package_layout['www'],
                              'fonts')
        copy_tree(root, target)

        # The generated_fonts.css file must be handled separately,
        # because each font alone specifies a generated_fonts.css
        # but it has to be appended, and not rewritten by subsequent
        # copies. The file also goes to style/, not fonts/
        with open(os.path.join(package_root,
                               package_layout['www'],
                               "style", "generated_fonts.css"), 'a') as style:
            with open(os.path.join(root, "generated_fonts.css"), 'r') as css:
                style.write(css.read() + "\n")

    # CodeChecker main scripts.
    LOG.debug('Copy main codechecker files')
    source = os.path.join(repository_root, 'bin', 'CodeChecker.py')
    target = os.path.join(package_root, package_layout['cc_bin'])
    shutil.copy2(source, target)

    source = os.path.join(repository_root, 'bin', 'CodeChecker')
    target = os.path.join(package_root, package_layout['bin'])
    shutil.copy2(source, target)

    # CodeChecker db migrate.
    LOG.debug('Copy codechecker database migration')
    source = os.path.join(repository_root, 'db_migrate')
    target = os.path.join(package_root,
                          package_layout['codechecker_db_migrate'])
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

    build_package(repository_root, build_package_config)
