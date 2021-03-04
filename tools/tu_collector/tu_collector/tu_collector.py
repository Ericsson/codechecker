#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Sometimes it might be useful to collect the source files constituting a
translation unit. This script does this action based on a compilation database
JSON file. The output of the script is a ZIP package with the collected
sources.
"""


import argparse
import collections
import fnmatch
import hashlib
import json
import logging
import os
import random
import re
import shlex
import string
import subprocess
import sys
import zipfile
from distutils.spawn import find_executable

from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Set, Tuple, Union

if sys.version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from mypy_extensions import TypedDict


LOG = logging.getLogger('tu_collector')

handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] - %(message)s')
handler.setFormatter(formatter)

LOG.setLevel(logging.INFO)
LOG.addHandler(handler)


class CompileAction(TypedDict):
    file: str
    command: str
    directory: str


CompilationDB = List[CompileAction]


def __random_string(length: int) -> str:
    """
    This function returns a random string of ASCII lowercase characters with
    the given length.
    """
    return ''.join(random.choice(string.ascii_lowercase)
                   for i in range(length))


def __get_toolchain_compiler(command: List[str]) -> Optional[str]:
    """
    Clang can be given a GCC toolchain so that the standard libs of that GCC
    are used. This function returns the path of the GCC toolchain compiler.
    """
    for cmp_opt in command:
        tcpath = re.match(r"^--gcc-toolchain=(?P<tcpath>.*)$", cmp_opt)
        if tcpath:
            is_cpp = '++' in command[0] or 'cpp' in command[0]
            return os.path.join(tcpath.group('tcpath'),
                                'bin',
                                'g++' if is_cpp else 'gcc')
    return None


def __determine_compiler(gcc_command: List[str]) -> str:
    """
    This function determines the compiler from the given compilation command.
    If the first part of the gcc_command is ccache invocation then the rest
    should be a complete compilation command.

    CCache may have three forms:
    1. ccache g++ main.cpp
    2. ccache main.cpp
    3. /usr/lib/ccache/gcc main.cpp
    In the first case this function drops "ccache" from gcc_command and returns
    the next compiler name.
    In the second case the compiler can be given by config files or an
    environment variable. Currently we don't handle this version, and in this
    case the compiler remanis "ccache" and the gcc_command is not changed.
    The two cases are distinguished by checking whether the second parameter is
    an executable or not.
    In the third case gcc is a symlink to ccache, but we can handle
    it as a normal compiler.

    gcc_command -- A split build action as a list which may or may not start
                   with ccache.

    !!!WARNING!!! This function must always return an element of gcc_command
    without modification (symlink resolve, absolute path conversion, etc.)
    otherwise an exception is thrown at the caller side.

    TODO: The second case could be handled if there was a way for querying the
    used compiler from ccache. This can be configured for ccache in config
    files or environment variables.
    """
    if gcc_command[0].endswith('ccache'):
        if find_executable(gcc_command[1]) is not None:
            return gcc_command[1]

    return gcc_command[0]


def __gather_dependencies(
    cmd: Union[str, List[str]],
    build_dir: str
) -> List[str]:
    """
    Returns a list of files which are contained in the translation unit built
    by the given build command.

    cmd -- The build command as a string or as a list that can be given to
           subprocess.Popen(). The first element is the executable
           compiler.
    build_dir -- The path of the working directory where the build command was
                 emitted.
    """

    def __eliminate_argument(
        arg_vect: List[str],
        opt_string: str,
        has_arg=False
    ) -> List[str]:
        """
        This call eliminates the parameters matching the given option string,
        along with its argument coming directly after the opt-string if any,
        from the command. The argument can possibly be separated from the flag.
        """
        while True:
            option_index = next(
                (i for i, c in enumerate(arg_vect)
                 if c.startswith(opt_string)), None)

            if option_index:
                separate = 1 if has_arg and \
                    len(arg_vect[option_index]) == len(opt_string) else 0
                arg_vect = arg_vect[0:option_index] + \
                    arg_vect[option_index + separate + 1:]
            else:
                break

        return arg_vect

    command = shlex.split(cmd) if isinstance(cmd, str) else cmd

    # gcc and clang can generate makefile-style dependency list.

    # If an output file is set, the dependency is not written to the
    # standard output but rather into the given file.
    # We need to first eliminate the output from the command.
    command = __eliminate_argument(command, '-o', True)
    command = __eliminate_argument(command, '--output', True)

    # This flag can be given a .specs file which contains the config options of
    # cc1, cc1plus, as, ld, etc. Sometimes this file is just a temporary during
    # the compilation. However, if the file doesn't exist, this flag fails the
    # compilation. Since this flag is not necessary for dependency generation,
    # we can skip it.
    command = __eliminate_argument(command, '-specs')

    # Remove potential dependency-file-generator options from the string
    # too. These arguments found in the logged build command would derail
    # us and generate dependencies, e.g. into the build directory used.
    command = __eliminate_argument(command, '-MM')
    command = __eliminate_argument(command, '-MF', True)
    command = __eliminate_argument(command, '-MP')
    command = __eliminate_argument(command, '-MT', True)
    command = __eliminate_argument(command, '-MQ', True)
    command = __eliminate_argument(command, '-MD')
    command = __eliminate_argument(command, '-MMD')

    # Clang contains some extra options.
    command = __eliminate_argument(command, '-MJ', True)
    command = __eliminate_argument(command, '-MV')

    # Build out custom invocation for dependency generation.
    compiler = __determine_compiler(command)
    command = [compiler, '-E', '-M', '-MT', '__dummy'] \
        + command[command.index(compiler) + 1:]

    # Remove empty arguments
    command = [i for i in command if i]

    # gcc does not have '--gcc-toolchain' argument it would fail if it is
    # kept there.
    # For clang it does not change the output, the include paths from
    # the gcc-toolchain are not added to the output.
    command = __eliminate_argument(command, '--gcc-toolchain')

    LOG.debug("Command: %s", ' '.join(command))

    try:
        output = subprocess.check_output(
            command,
            cwd=build_dir,
            encoding="utf-8",
            errors="replace")
        rc = 0
    except subprocess.CalledProcessError as ex:
        output, rc = ex.output, ex.returncode
    except OSError as oerr:
        output, rc = oerr.strerror, oerr.errno

    if rc != 0:
        raise IOError(output)

    # Parse 'Makefile' syntax dependency output.
    dependencies = output.replace('__dummy: ', '') \
        .replace('\\', '') \
        .replace('  ', '') \
        .replace(' ', '\n')

    # The dependency list already contains the source file's path.
    return [os.path.join(build_dir, dep) for dep in
            dependencies.splitlines() if dep != ""]


def __analyzer_action_hash(build_action: CompileAction) -> str:
    """
    This function returns a hash of a build action. This hash algorithm is
    duplicated based on the same algorithm in CodeChecker. It is important to
    keep these algorithms in sync!!! Basically the hash is computed from the
    build command except for -o flag. The exclusion is due to a special
    behavior of "make" utility. See the full description in CodeChecker:
    analyzer_action_str() contains the documentation of the issue.
    """
    source_file = os.path.normpath(
        os.path.join(build_action['directory'], build_action['file']))

    args = shlex.split(build_action['command'])
    indices = [idx for idx, v in enumerate(args) if v.startswith('-o')]

    for idx in reversed(indices):
        # Output can be given separate or joint:
        # -o a.out vs -oa.out
        # In the first case we delete its argument too.
        if args[idx] == '-o':
            del args[idx]
        del args[idx]

    build_info = source_file + '_' + ' '.join(args)

    return hashlib.md5(build_info.encode(errors='ignore')).hexdigest()


def __get_ctu_buildactions(
    build_action: CompileAction,
    compilation_db: CompilationDB,
    ctu_deps_dir: str
) -> Iterator[CompileAction]:
    """
    CodeChecker collets which source files were involved in CTU analysis. This
    function returns the build actions which describe the compilation of these
    files.
    build_action -- The build action object which is analyzed in CTU mode. Its
                    CTU dependencies will be returned.
    compilation_db -- A complete compilation database. This function returns
                      some of its elements: the ones which describe the
                      compilation of the files listed in the file under
                      ctu_deps_dir belonging to build_action.
    ctu_deps_dir -- A directory created by CodeChecker under the report
                    directory. The files under this folder must contain a hash
                    of a build action. See __analyzer_action_hash().
    """
    ctu_deps_file = next(
        (f for f in os.listdir(ctu_deps_dir)
         if __analyzer_action_hash(build_action) in f), None)

    if not ctu_deps_file:
        return iter(())

    with open(os.path.join(ctu_deps_dir, ctu_deps_file),
              encoding='utf-8', errors='ignore') as f:
        files = list(map(lambda x: x.strip(), f.readlines()))

    return filter(
        lambda ba: os.path.join(ba['directory'], ba['file']) in files,
        compilation_db)


def get_dependent_headers(
    command: Union[str, List[str]],
    build_dir_path: str,
    collect_toolchain=True
) -> Tuple[Set[str], str]:
    """
    Returns a pair of which the first component is a set of files building up
    the translation unit and the second component is an error message which is
    not empty in case some files may be missing from the set.

    command -- The build command as a string or as a list that can be given to
               subprocess.Popen(). The first element is the executable
               compiler.
    build_dir_path -- The path of the working directory where the build command
                      was emitted.
    collect_toolchain -- If the given command uses Clang and it is given a GCC
                         toolchain then the toolchain compiler's dependencies
                         are also collected in case this parameter is True.
    """

    LOG.debug("Generating dependent headers via compiler...")

    if isinstance(command, str):
        command = shlex.split(command)

    dependencies = set()
    error = ''

    try:
        dependencies |= set(__gather_dependencies(command, build_dir_path))
    except Exception as ex:
        LOG.error("Couldn't create dependencies: %s", str(ex))
        error += str(ex)

    toolchain_compiler = __get_toolchain_compiler(command)

    if collect_toolchain and toolchain_compiler:
        LOG.debug("Generating gcc-toolchain headers via toolchain "
                  "compiler...")
        try:
            # Change the original compiler to the compiler from the toolchain.
            command[0] = toolchain_compiler
            dependencies |= set(__gather_dependencies(command, build_dir_path))
        except Exception as ex:
            LOG.error("Couldn't create dependencies: %s", str(ex))
            error += str(ex)

    LOG.debug("Dependencies: %s", ', '.join(dependencies))
    return dependencies, error


def add_sources_to_zip(
    zip_file: Union[str, Path],
    files: Union[str, Iterable[str]]
):
    """
    This function adds source files to the ZIP file if those are not present
    yet. The files will be placed to the "sources-root" directory under the ZIP
    file.

    zip_file -- A ZIP file name as a string.
    files -- A file path or an iterable of file paths.
    """
    if isinstance(files, str):
        files = [files]

    with zipfile.ZipFile(zip_file, 'a') as archive:
        for f in files:
            archive_path = os.path.normpath(
                os.path.join('sources-root', f.lstrip(os.sep)))

            try:
                archive.getinfo(archive_path)
            except KeyError:
                archive.write(f, archive_path, zipfile.ZIP_DEFLATED)
            else:
                LOG.debug("'%s' is already in the ZIP file, won't add it "
                          "again!", f)


def zip_tu_files(
    zip_file: Union[str, Path],
    compilation_db: Union[str, CompilationDB],
    file_filter='*',
    write_mode='w',
    ctu_deps_dir: Optional[str] = None
):
    """
    Collects all files to a zip file which are required for the compilation of
    the translation units described by the given compilation database.
    If there are some files which couldn't be collected then a "no-sources"
    file will contain the error message of its reason.
    The function returns the set of files.

    zip_file -- A file name or a file object.
    compilation_database -- Either a path of the compilation database JSON file
                            or a list of the parsed JSON.
    file_filter -- A glob used as file name filter. The files of a TU will be
                   collected only if the "file" attribute of the build action
                   matches this glob.
    write_mode -- The file opening mode of the zip_file. In case of 'a' the new
                  files are appended to the existing zip file, in case of 'w'
                  the files are added to a clean zip file.
    ctu_deps_dir -- This directory contains a list of files. Each file belongs
                    to a translation unit and lists what other files are
                    involved during CTU analysis. These files and their
                    included headers will also be compressed in the .zip file.
                    File names in this directory must contain a hash of a the
                    build command. See __analyzer_action_hash() documentation.
                    When using this options, make sure to provide a compilation
                    database in the first argument which contains the build
                    commands of these files otherwise the files of this folder
                    can't be identified.
    """
    if isinstance(compilation_db, str):
        with open(compilation_db, encoding="utf-8", errors="ignore") as f:
            compilation_database = json.load(f)
    else:
        compilation_database = compilation_db

    no_sources = 'no-sources'
    tu_files: Set[str] = set()
    error_messages = ''

    filtered_compilation_database = list(filter(
        lambda action: fnmatch.fnmatch(action['file'], file_filter),
        compilation_database))

    if ctu_deps_dir:
        involved_ctu_actions: List[CompileAction] = []

        for action in filtered_compilation_database:
            involved_ctu_actions.extend(__get_ctu_buildactions(
                action, compilation_database, ctu_deps_dir))

        for action in involved_ctu_actions:
            if action not in filtered_compilation_database:
                filtered_compilation_database.append(action)

    for buildaction in filtered_compilation_database:
        files, err = get_dependent_headers(
            buildaction['command'],
            buildaction['directory'])

        tu_files |= files

        if err:
            error_messages += buildaction['file'] + '\n' \
                + '-' * len(buildaction['file']) + '\n' + err + '\n'

    if write_mode == 'a' and os.path.isfile(zip_file):
        with zipfile.ZipFile(zip_file) as archive:
            try:
                archive.getinfo(no_sources)
            except KeyError:
                pass
            else:
                no_sources = 'no-sources_' + __random_string(5)

    if error_messages:
        with zipfile.ZipFile(zip_file, write_mode) as archive:
            archive.writestr(no_sources, error_messages)
    elif write_mode == 'w':
        try:
            os.remove(zip_file)
        except OSError:
            pass

    add_sources_to_zip(zip_file, tu_files)

    with zipfile.ZipFile(zip_file, 'a') as archive:
        archive.writestr('compilation_database.json',
                         json.dumps(compilation_database, indent=2))


def get_dependent_sources(
    compilation_db: CompilationDB,
    header_path: Optional[str] = None
) -> Set[str]:
    """ Get dependencies for each files in each translation unit. """
    dependencies = collections.defaultdict(set)
    for build_action in compilation_db:
        files, _ = get_dependent_headers(
            build_action['command'],
            build_action['directory'])

        source_file = os.path.join(build_action['directory'],
                                   build_action['file'])
        for f in files:
            dependencies[f].add(source_file)

    pattern = None
    if header_path:
        norm_header_path = os.path.normpath(header_path.strip())
        pattern = re.compile(fnmatch.translate(norm_header_path))

    deps = set()
    for header, source_files in dependencies.items():
        if not pattern or pattern.match(header):
            deps.update(source_files)

    return deps


def main():
    # --- Handling of command line arguments --- #

    parser = argparse.ArgumentParser(
        description="""
This script can be used for multiple purposes:
- It can be used to collect all the source files constituting specific
translation units. The files are written to a ZIP file which will contain the
sources preserving the original directory hierarchy.
- It can be used to get source files which depend on a given header file.""",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    log_args = parser.add_argument_group(
        "log arguments",
        """
Specify how the build information database should be obtained. You need to
specify either an already existing log file, or a build command which will be
used to generate a log file on the fly.""")
    log_args = log_args.add_mutually_exclusive_group(required=True)

    log_args.add_argument('-b', '--build', type=str, dest='command',
                          help="Execute and record a build command. Build "
                               "commands can be simple calls to 'g++' or "
                               "'clang++'.")
    log_args.add_argument('-l', '--logfile', type=str, dest='logfile',
                          help="Use an already existing JSON compilation "
                               "command database file specified at this path.")

    parser.add_argument('-f', '--filter', dest='filter',
                        type=str, required=False, default='*',
                        help="If '--zip' option is given this flag restricts "
                             "the collection on the build actions of which "
                             "the compiled source file matches this path. "
                             "If '--dependents' option is given this flag "
                             "specify a header file to get source file "
                             "dependencies for. E.g.: /path/to/*/files")
    parser.add_argument('--ctu-deps-dir', dest='ctu_deps_dir',
                        type=str, required=False,
                        help="When using 'CodeChecker analyze --ctu' command, "
                             "the results go to an output directory. This "
                             "folder contains a directory named "
                             "'ctu_connections' which stores the information "
                             "what TUs are involved during the analysis of "
                             "each source file. Once this directory is "
                             "provided, this tool also collects the sourced "
                             "of TUs involved by CTU analysis.")

    output_args = parser.add_argument_group(
        "output arguments",
        "Specify the output type.")

    output_args = output_args.add_mutually_exclusive_group(required=True)
    output_args.add_argument('-z', '--zip', dest='zip', type=str,
                             help="Output ZIP file.")

    output_args.add_argument('-d', '--dependents', dest='dependents',
                             action='store_true',
                             help="Use this flag to return a list of source "
                                  "files which depend on some header files "
                                  "specified by the --filter option. The "
                                  "result will not contain header files, even "
                                  "if those are dependents as well.")

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        dest='verbose',
                        help="Enable debug level logging.")

    args = parser.parse_args()

    # --- Checking the existence of input files. --- #

    if 'verbose' in args and args.verbose:
        LOG.setLevel(logging.DEBUG)

    if args.logfile and not os.path.isfile(args.logfile):
        LOG.error("Compilation database file doesn't exist: %s", args.logfile)
        sys.exit(1)

    # --- Do the job. --- #

    if args.logfile:
        with open(args.logfile, encoding="utf-8", errors="ignore") as f:
            compilation_db = json.load(f)
    else:
        compilation_db = [{
            'file': '',
            'command': args.command,
            'directory': os.getcwd()}]

    if args.zip:
        if args.command and args.filter:
            LOG.warning('In case of using build command --filter has no '
                        'effect.')
        if args.command and args.ctu_deps_dir:
            LOG.warning('In case of using build command --ctu-deps-dir has no '
                        'effect.')

        zip_tu_files(args.zip, compilation_db, args.filter,
                     ctu_deps_dir=args.ctu_deps_dir)
        LOG.info("Done.")
    else:
        deps = get_dependent_sources(compilation_db, args.filter)

        if deps:
            print("\n".join(deps))
        else:
            LOG.info("No source file dependencies.")


if __name__ == "__main__":
    main()
