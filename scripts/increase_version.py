#!/usr/bin/env python
"""
Automated script for updating various versioning-related parts of CodeChecker.
"""

import argparse
import atexit
import json
import logging
import os
import shutil
import subprocess
import sys


LOG = logging.getLogger('VERSION INCREASE')
msg_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
log_handler = logging.StreamHandler()
log_handler.setFormatter(msg_formatter)
LOG.setLevel(logging.INFO)
LOG.addHandler(log_handler)


def __get_argparser():
    """
    Create the command-line argument parser for this module.
    """

    parser = argparse.ArgumentParser(
        description="Increase some of the version-related information of "
                    "CodeChecker. This tool must be ran in a developer "
                    "working directory, which must be clean for safety "
                    "reasons. Not every change can be made automatically, so "
                    "this script outputs follow-up action points to take "
                    "before contributing the version increase to the code "
                    "base!",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='store_true',
                        default=argparse.SUPPRESS,
                        help="Print more information about the actions "
                             "being taken.")

    cc_ver = parser.add_argument_group("CodeChecker version arguments")
    cc_ver = cc_ver.add_mutually_exclusive_group(required=True)

    cc_ver.add_argument('--major',
                        dest='cc_ver',
                        action='store_const',
                        const='major',
                        default=argparse.SUPPRESS,
                        help="Increase the major version of CodeChecker, "
                             "signifying a considerable change in the "
                             "software. This mode will set 'minor' and "
                             "'revision' to 0. NOTICE: Specifying --major "
                             "will automatically specify the other '-major' "
                             "options, such as --api-major, --pdb-major, and "
                             "--rdb-major.")

    cc_ver.add_argument('--minor',
                        dest='cc_ver',
                        action='store_const',
                        const='minor',
                        default=argparse.SUPPRESS,
                        help="Increase only the minor version. This "
                             "option is usually used when new features are "
                             "added without compatibility breaking. This "
                             "mode will set 'revision' to 0.")

    cc_ver.add_argument('--revision',
                        dest='cc_ver',
                        action='store_const',
                        const='revision',
                        default=argparse.SUPPRESS,
                        help="Increase only the revision, which signifies "
                             "only minimal bug fixes and polishes in the "
                             "upcoming release, without any actual feature "
                             "additions.")

    api_ver = parser.add_argument_group("Thrift API version arguments")

    api_ver = api_ver.add_mutually_exclusive_group(required=False)

    api_ver.add_argument('--api-major',
                         dest='api_ver',
                         action='store_const',
                         const='major',
                         default=argparse.SUPPRESS,
                         help="Increase the major version. This mode will "
                              "set 'minor' to 0.")

    api_ver.add_argument('--api-minor',
                         dest='api_ver',
                         action='store_const',
                         const='minor',
                         default=argparse.SUPPRESS,
                         help="Increase the minor version.")

    def __handle(args):
        """
        Custom argument handler for this script to give invocation-related
        error messages and apply extra rules that can not be expressed
        with argparse.
        """

        def arg_match(options):
            """
            Checks and selects the option strings specified in 'options'
            that are present in the invocation.
            """

            matched_args = []
            for option in options:
                if any([arg if option.startswith(arg) else None
                        for arg in sys.argv[1:]]):
                    matched_args.append(option)
                    continue

            return matched_args

        if args.cc_ver == 'major':
            # CodeChecker major version increase automatically implies a
            # major version increase on everything else.

            minor_opts = ['--api-minor']
            matching = arg_match(minor_opts)
            if any(matching):
                first_matching = next(iter([match for match in matching]))
                parser.error("argument {0}: not allowed with argument "
                             "--major".format(first_matching))
                # parser.error() terminates with return code 2.

            setattr(args, 'api_ver', 'major')

        __main__(args)

    parser.set_defaults(func=__handle)
    return parser


def increase_version(version_dict, attribute):
    new_value = str(int(version_dict[attribute]) + 1)
    version_dict[attribute] = new_value


def format_version2(version):
    return "{0}.{1}".format(version['major'],
                            version['minor'])


def split_version2(version):
    parts = version.split('.')
    return {'major': parts[0], 'minor': parts[1]}


def format_version3(version):
    return "{0}.{1}.{2}".format(version['major'],
                                version['minor'],
                                version['revision'])


def __try_command(command, extra_error):
    try:
        return subprocess.check_output(command)
    except (subprocess.CalledProcessError, OSError) as err:
        LOG.debug("Failed to run command: {0}".format(' '.join(command)))
        LOG.debug(str(err))
        LOG.error(extra_error)
        sys.exit(1)


def __handle_api_version(args, paths_to_clean_up, paths_to_keep_at_success,
                         paths_to_move, followups):
    # Handle API version increases.
    if 'api_ver' in args:
        libcc_vpath = os.path.join('libcodechecker', 'version.py')
        scope = {}
        with open(libcc_vpath, 'r') as libcc_vfile:
            exec(libcc_vfile.read(), scope)

        # Execute the version library's code, which will give us the current
        # API version string and the supported versions in a dict.
        versions = scope['SUPPORTED_VERSIONS']
        version = split_version2(scope['CLIENT_API'])
        old_ver = format_version2(version)

        if args.api_ver == 'minor':
            # Minor version increase only results in the supported version
            # tokens' update automatically.
            increase_version(version, 'minor')
            versions[int(version['major'])] = version['minor']

            followups.append("Add the definitions of the new API "
                             "functions in 'api/v{0}', and the relevant "
                             "stubs, and handler functions in the client "
                             "and the server.".format(version['major']))
            followups.append("Add the definitions of the new API functions "
                             "in 'api/v{0}'.".format(version['major']))
            followups.append("Add the function handlers in 'libcodechecker/"
                             "server/api' files.")
            followups.append("Add the function stubs in 'libcodechecker/"
                             "libclient' helper modules.")
            followups.append("Make use of the new functions you've just "
                             "added in either clients.")
        elif args.api_ver == 'major':
            old_major = version['major']
            increase_version(version, 'major')
            version['minor'] = 0
            versions[int(version['major'])] = 0

            # Major API changes involve a new 'api/vX' subfolder.
            old_folder = os.path.join('api', 'v{0}'.format(old_major))
            new_folder = os.path.join('api', 'v{0}'.format(version['major']))
            shutil.copytree(old_folder, new_folder)

            paths_to_clean_up.append(new_folder)
            paths_to_keep_at_success.append(new_folder)

            # Major API changes involve a new
            # 'libcodechecker/server/api/vX' subfolder.
            folder_root = os.path.join('libcodechecker', 'server', 'api')
            old_folder = os.path.join(folder_root, 'v{0}'.format(old_major))
            new_folder = os.path.join(folder_root,
                                      'v{0}'.format(version['major']))
            shutil.copytree(old_folder, new_folder)

            paths_to_clean_up.append(new_folder)
            paths_to_keep_at_success.append(new_folder)

            followups.append("Add the definitions of the new API functions "
                             "in 'api/v{0}'.".format(version['major']))
            followups.append("Create the API handlers in 'libcodechecker/"
                             "server/api/v{0}', and implement the handler "
                             "functions for the new API."
                             .format(version['major']))
            followups.append("Implement importing the new API handlers in "
                             "'libcodechecker/server/server.py', along with "
                             "an appropriate handler instantiation in the "
                             "do_POST() method.")
            followups.append("Change 'libcodechecker/client' to use the "
                             "new API. This involves changing the 'import' "
                             "statements' '_v{0}' suffix to '_v{1}'."
                             .format(old_major, version['major']))
            followups.append("Change the Web GUI's main files, such as "
                             "'www/scripts/codecheckerviewer/"
                             "codecheckerviewer.js', to import the new, "
                             "'_v{0}' suffix Thrift stubs."
                             .format(version['major']))
            followups.append("Make use of the new functions you've just "
                             "added in either clients.")
            followups.append("Update the 'tests/' code to use the new API "
                             "functions.")
            followups.append("Optional: Deprecate an older API version by "
                             "editing the server's do_POST() method, "
                             "removing the API handlers and their imports, "
                             "removing the 'api/vX' subfolder, and deleting "
                             "the major version's row from 'libcodechecker/"
                             "version.py'.")

        new_ver = format_version2(version)
        supported_versions = [format_version2({'major': ver,
                                               'minor': versions[ver]})
                              for ver in versions]
        LOG.info("API version: {0} -> {1}".format(old_ver, new_ver))
        LOG.info("API versions marked as supported serverside: {0}"
                 .format(', '.join(supported_versions)))

        # Create a new version module with the updated SUPPORTED_VERSIONS
        # dict.
        libcc_vpath = os.path.join('libcodechecker', 'version.py')
        with open(libcc_vpath, 'r') as cc_vfile_old:
            idx = 0
            lines = cc_vfile_old.readlines()
            # Copy lines before SUPPORTED_VERSIONS.
            for line in lines:
                if line.startswith('SUPPORTED_VERSIONS'):
                    break
                idx = idx + 1

            lines_to_write = lines[:idx]

            # Format a new dict into the source code, based on the
            # supported versions calculated.
            supported_vers = ['SUPPORTED_VERSIONS = {\n']
            for ver in versions:
                supported_vers.append('    {0}: {1},\n'
                                      .format(ver, versions[ver]))
            supported_vers[-1] = supported_vers[-1].replace(',\n', '\n')
            supported_vers.append('}\n')

            lines_to_write = lines_to_write + supported_vers

            # Skip until the end of the original dict's code block,
            # and copy the remainder of the file.
            lines = lines[idx:]
            idx = 0
            for line in lines:
                idx = idx + 1
                if line.strip() == '}':
                    break

            lines_to_write = lines_to_write + lines[idx:]

            with open(libcc_vpath + '.2', 'w') as cc_vfile_new:
                paths_to_clean_up.append(libcc_vpath + '.2')
                paths_to_move[libcc_vpath + '.2'] = libcc_vpath

                cc_vfile_new.writelines(lines_to_write)

        # Update the WebGUI's definition file to the latest version.
        webgui_vpath = os.path.join('www', 'scripts', 'version.js')
        with open(webgui_vpath, 'r') as wg_vfile_old:
            with open(webgui_vpath + '.2', 'w') as wg_vfile_new:
                paths_to_clean_up.append(webgui_vpath + '.2')
                paths_to_move[webgui_vpath + '.2'] = webgui_vpath

                wg_vfile_new.write(wg_vfile_old.read()
                                   .replace(old_ver, new_ver))


def __main__(args):
    if 'verbose' in args:
        LOG.setLevel(logging.DEBUG)

    __try_command(['git', 'rev-parse', 'HEAD'],
                  "This script must be ran in from the a development working "
                  "directory, which is Git versioned.")
    __try_command([os.path.join('scripts', 'increase_version.py'), '--help'],
                  "This script must be ran in from the root of a development "
                  "working directory.")

    output = __try_command(['git', 'status', '--porcelain',
                            '--untracked-files=no'],
                           "Failed to check if working directory is clean. "
                           "Git installed badly?!")
    if len(output) > 0:
        LOG.error("The working directory must be clean, which means no "
                  "tracked files may contain local modifications.")
        LOG.error("Use 'git status' to see the changes you made, and either "
                  "stash or commit them.")
        sys.exit(1)

    subprocess.call(['git', 'status'])

    LOG.info("Begin CodeChecker package version increment...")
    LOG.debug(args)

    paths_to_move = {}
    paths_to_clean_up = []
    paths_to_keep_at_success = []

    def __cleanup():
        """
        Custom exit handler which cleans up intermittent files created
        by the upgrade script. This routine also makes version increase
        atomic, as the new files are only replacing the old ones if
        every operation was successful.
        """

        LOG.debug("Removing intermittent files created by script")
        for p in paths_to_clean_up:
            LOG.debug("Cleaning up '{0}'...".format(p))
            if os.path.isfile(p):
                os.remove(p)
            elif os.path.isdir(p):
                shutil.rmtree(p)

    atexit.register(__cleanup)

    # Follow-up action points to print for the user, marking things to be done
    # to properly implement the version change.
    followups = []

    # Handle cc_ver first.
    try:
        with open(os.path.join('config', 'version.json'), 'r') as vfile:
            vdict = json.load(vfile)
    except Exception:
        LOG.error("Cannot open the 'config/version.json' file.")
        sys.exit(1)

    version = vdict['version']
    old_ver = format_version3(version)

    if args.cc_ver == 'revision':
        LOG.debug("Increasing CodeChecker revision")
        increase_version(version, 'revision')
    elif args.cc_ver == 'minor':
        LOG.debug("Increasing CodeChecker minor version")
        increase_version(version, 'minor')
        version['revision'] = "0"
    elif args.cc_ver == 'major':
        LOG.debug("Increasing CodeChecker major version")
        increase_version(version, 'major')
        version['minor'] = "0"
        version['revision'] = "0"

    new_ver = format_version3(version)
    LOG.info("CodeChecker version: {0} -> {1}".format(old_ver, new_ver))

    # Update Doxyfile.in
    with open('Doxyfile.in', 'r') as doxy_old:
        with open('Doxyfile.in.2', 'w') as doxy_new:
            paths_to_clean_up.append(os.path.abspath('Doxyfile.in.2'))
            paths_to_move[os.path.abspath('Doxyfile.in.2')] = \
                os.path.abspath('Doxyfile.in')

            for line in doxy_old:
                if line.startswith('PROJECT_NUMBER'):
                    line = line.replace(old_ver, new_ver)
                    LOG.info("CodeChecker version in documentation.")
                doxy_new.write(line)

    # Save the version configuration into an intermittent file.
    vpath = os.path.join('config', 'version.json.2')
    with open(vpath, 'w') as vfile:
        paths_to_clean_up.append(vpath)
        paths_to_move[vpath] = os.path.join('config', 'version.json')

        json.dump(vdict, vfile, indent=2, sort_keys=True)

    __handle_api_version(args, paths_to_clean_up, paths_to_keep_at_success,
                         paths_to_move, followups)

    # If everything was successful, handle the paths_ lists.
    LOG.info("Finalising changes...")

    # Certain files must not be removed by the clean-up routine.
    paths_to_clean_up = list(set(paths_to_clean_up) -
                             set(paths_to_keep_at_success))

    # Certain files must be renamed to be in an appropriate location.
    for p in paths_to_move:
        t = paths_to_move[p]
        LOG.debug("Moving '{0}' to '{1}'...".format(p, t))
        os.rename(p, t)

    # Further files will be cleaned up by the atexit routine.
    LOG.info("Automatic version increment done.")

    # Show action points to the user.
    if len(followups) > 0:
        LOG.warning("!!! YOUR JOB DOES NOT END HERE !!!")
        LOG.info("There are a few things still to be done before the new "
                 "version can be submitted to the codebase:")

        with open('VERSION_TODO.md', 'w') as f:
            f.write("TO-DO before the version change can be applied "
                    "upstream\n")
            f.write("======================================================="
                    "\n\n")

            def __print_and_save(line):
                print(line)
                f.write(line)
                f.write('\n')

            for ap in followups:
                __print_and_save(" * " + ap[:75])
                ap = ap[75:]
                while len(ap) > 0:
                    __print_and_save("   " + ap[:75])
                    ap = ap[75:]

            f.write('\n * Remove this file!\n')

    # Prepare the changed files for the next 'git commit'.
    LOG.debug("Adding changes to Git index...")
    for p in set(paths_to_move.values()).union(set(paths_to_keep_at_success)):
        LOG.debug("Adding '{0}' to index...".format(p))
        subprocess.call(['git', 'add', p])

    subprocess.call(['git', 'add', 'VERSION_TODO.md'])

    # Let the user see what files have been changed by the script.
    LOG.info("Changes made by automatic script:")
    subprocess.call(['git', 'status'])


if __name__ == "__main__":
    parser = __get_argparser()
    args = parser.parse_args()
    args.func(args)
