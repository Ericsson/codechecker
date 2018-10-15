# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
import codecs
import json
import logging
import os
import random
import re
import shlex
import string
import subprocess
import zipfile


def __random_string(l):
    """
    This function returns a random string of ASCII lowercase characters with
    the given length.
    """
    return ''.join(random.choice(string.ascii_lowercase) for i in range(l))


def __get_toolchain_compiler(command):
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


def __gather_dependencies(command, build_dir):
    """
    Returns a list of files which are contained in the translation unit built
    by the given build command.

    command -- The build command as a string or as a list that can be given to
               subprocess.Popen(). The first element is the executable
               compiler.
    build_dir -- The path of the working directory where the build command was
                 emitted.
    """

    def __eliminate_argument(arg_vect, opt_string, has_arg=False):
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

    if isinstance(command, basestring):
        command = shlex.split(command)

    # gcc and clang can generate makefile-style dependency list.

    # If an output file is set, the dependency is not written to the
    # standard output but rather into the given file.
    # We need to first eliminate the output from the command.
    command = __eliminate_argument(command, '-o', True)
    command = __eliminate_argument(command, '--output', True)

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
    command = [command[0], '-E', '-M', '-MT', '__dummy'] + command[1:]

    # Remove empty arguments
    command = [i for i in command if i]

    # gcc does not have '--gcc-toolchain' argument it would fail if it is
    # kept there.
    # For clang it does not change the output, the include paths from
    # the gcc-toolchain are not added to the output.
    command = __eliminate_argument(command, '--gcc-toolchain')

    try:
        output = subprocess.check_output(command,
                                         bufsize=-1,
                                         stderr=subprocess.STDOUT,
                                         cwd=build_dir)
        rc = 0
    except subprocess.CalledProcessError as ex:
        output, rc = ex.output, ex.returncode
    except OSError as oerr:
        output, rc = oerr.strerror, oerr.errno

    output = codecs.decode(output, 'utf-8', 'replace')
    if rc == 0:
        # Parse 'Makefile' syntax dependency output.
        dependencies = output.replace('__dummy: ', '') \
            .replace('\\', '') \
            .replace('  ', '') \
            .replace(' ', '\n')

        # The dependency list already contains the source file's path.
        return [os.path.join(build_dir, dep) for dep in
                dependencies.splitlines() if dep != ""]
    else:
        raise IOError(output)


def get_dependent_headers(command, build_dir, collect_toolchain=True):
    """
    Returns a pair of which the first component is a set of files building up
    the translation unit and the second component is an error message which is
    not empty in case some files may be missing from the set.

    command -- The build command as a string or as a list that can be given to
               subprocess.Popen(). The first element is the executable
               compiler.
    build_dir -- The path of the working directory where the build command was
                 emitted.
    collect_toolchain -- If the given command uses Clang and it is given a GCC
                         toolchain then the toolchain compiler's dependencies
                         are also collected in case this parameter is True.
    """

    logging.debug("Generating dependent headers via compiler...")

    if isinstance(command, basestring):
        command = shlex.split(command)

    dependencies = set()
    error = ''

    try:
        dependencies |= set(__gather_dependencies(command, build_dir))
    except Exception as ex:
        logging.debug("Couldn't create dependencies:")
        logging.debug(str(ex))
        error += str(ex)

    toolchain_compiler = __get_toolchain_compiler(command)

    if collect_toolchain and toolchain_compiler:
        logging.debug("Generating gcc-toolchain headers via toolchain "
                      "compiler...")
        try:
            # Change the original compiler to the compiler from the toolchain.
            command[0] = toolchain_compiler
            dependencies |= set(__gather_dependencies(command, build_dir))
        except Exception as ex:
            logging.debug("Couldn't create dependencies:")
            logging.debug(str(ex))
            error += str(ex)

    return dependencies, error


def add_sources_to_zip(zip_file, files):
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
            archive_path = os.path.join('sources-root', f.lstrip(os.sep))

            try:
                archive.getinfo(archive_path)
            except KeyError:
                archive.write(f, archive_path, zipfile.ZIP_DEFLATED)
            else:
                logging.debug("'%s' is already in the ZIP file, won't add it "
                              "again!", f)


def zip_tu_files(zip_file, compilation_database, write_mode='w'):
    """
    Collects all files to a zip file which are required for the compilation of
    the translation units described by the given compilation database.
    If there are some files which couldn't be collected then a "no-sources"
    file will contain the error message of its reason.
    The function returns the set of files.

    zip_file -- A file name or a file object.
    compilation_database -- Either a path of the compilation database JSON file
                            or a list of the parsed JSON.
    write_mode -- The file opening mode of the zip_file. In case of 'a' the new
                  files are appended to the existing zip file, in case of 'w'
                  the files are added to a clean zip file.
    """
    if isinstance(compilation_database, basestring):
        with open(compilation_database) as f:
            compilation_database = json.load(f)

    no_sources = 'no-sources'
    tu_files = set()
    error_messages = ''

    for buildaction in compilation_database:
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

    add_sources_to_zip(zip_file, tu_files)
