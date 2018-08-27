# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Parse the compile_commands.json file.
Get compiler specific include paths targets.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import traceback

# TODO: This is a cross-subpackage import!
from libcodechecker.analyze import gcc_toolchain
from libcodechecker.log import build_action
from libcodechecker.log import option_parser
from libcodechecker.logger import get_logger
from libcodechecker.util import load_json_or_empty

LOG = get_logger('buildlogger')


# If these options are present in the original build command, they must
# be forwarded to get_compiler_includes and get_compiler_defines so the
# resulting includes point to the target that was used in the build.
COMPILE_OPTS_FWD_TO_DEFAULTS_GETTER = frozenset(
    ['^-m(32|64)',
     '^-std=.*'])

compiler_info_dump_file = "compiler_info.json"


def remove_file_if_exists(filename):
    if os.path.isfile(filename):
        os.remove(filename)


def get_compiler_err(cmd):
    """
    Returns the stderr of a compiler invocation as string.
    """
    try:
        proc = subprocess.Popen(shlex.split(cmd),
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        _, err = proc.communicate("")
        return err
    except OSError as oerr:
        LOG.error("Error during process execution: " + cmd + '\n' +
                  oerr.strerror + "\n")


def parse_compiler_includes(lines):
    '''
    Parse the compiler include paths from a string
    '''
    start_mark = "#include <...> search starts here:"
    end_mark = "End of search list."

    include_paths = []

    do_append = False
    for line in lines.splitlines(True):
        line = line.strip()
        if line.startswith(end_mark):
            break
        if do_append:
            # On OSX there are framework includes,
            # where we need to strip the "(framework directory)" string.
            # For instance:
            # /System/Library/Frameworks (framework directory)
            fpos = line.find("(framework directory)")
            if fpos == -1:
                include_paths.append(line)
            else:
                include_paths.append(line[0:fpos-1])

        if line.startswith(start_mark):
            do_append = True

    return include_paths


def filter_compiler_includes(include_dirs):
    """
    Filter the list of compiler includes.
    We want to elide GCC's include-fixed and instrinsic directory.
    See docs/gcc_incompatibilities.md
    """

    def contains_intrinsic_headers(include_dir):
        """
        Returns True if the given directory contains at least one intrinsic
        header.
        """
        if not os.path.exists(include_dir):
            return False
        for f in os.listdir(include_dir):
            if f.endswith("intrin.h"):
                return True
        return False

    result = []
    for include_dir in include_dirs:
        # Skip GCC's fixinclude dir
        if os.path.basename(os.path.normpath(include_dir)) == "include-fixed":
            continue
        if contains_intrinsic_headers(include_dir):
            continue
        result.append(include_dir)
    return result


def prepend_isystem_and_normalize(include_dirs):
    return ["-isystem " + os.path.normpath(idir) for idir in include_dirs]


def parse_compiler_target(lines):
    """
    Parse the compiler target from a string.

    """
    target_label = "Target:"
    target = ""

    for line in lines.splitlines(True):
        line = line.strip().split()
        if len(line) > 1 and line[0] == target_label:
            target = line[1]

    return target


def dump_compiler_info(filename, compiler, attr, data):
    all_data = dict()
    if os.path.exists(filename):
        all_data = load_json_or_empty(filename)
    if compiler not in all_data:
        all_data[compiler] = dict()
    all_data[compiler].update({attr: data})
    with open(filename, 'w') as f:
        json.dump(all_data, f)


def load_compiler_info(filename, compiler, attr):
    data = load_json_or_empty(filename, {})
    value = data.get(compiler)
    if value is None:
        LOG.error("Could not find compiler %s in file %s" %
                  (compiler, filename))
    return value.get(attr) if isinstance(value, dict) else value


def get_compiler_includes(parseLogOptions, compiler, lang, compile_opts,
                          extra_opts=None):
    """
    Returns a list of default includes of the given compiler.
    """
    if extra_opts is None:
        extra_opts = []

    # The first sysroot flag found among the compilation options is added
    # to the command below to give a more precise default include list.
    # Absence of any sysroot flags results in an empty string.
    sysroot = ""
    for i, item in enumerate(compile_opts):
        if item.startswith("--sysroot"):
            # len("--sysroot") == 9
            # len("--sysroot=") == 10
            sysroot = compile_opts[i + 1] if len(item) == 9 else item[10:]
            sysroot = "--sysroot=" + sysroot
            break

    cmd = compiler + " " + ' '.join(extra_opts) + " -E -x " + lang + \
        " " + sysroot + " - -v "

    err = ""
    if parseLogOptions.compiler_includes_file is None:
        LOG.debug("Retrieving default includes via '" + cmd + "'")
        err = get_compiler_err(cmd)
    else:
        err = load_compiler_info(parseLogOptions.compiler_includes_file,
                                 compiler,
                                 'includes')

    if parseLogOptions.output_path is not None:
        LOG.debug("Dumping default includes " + compiler)
        dump_compiler_info(compiler_info_dump_file,
                           compiler,
                           'includes',
                           err)
    return prepend_isystem_and_normalize(
        filter_compiler_includes(parse_compiler_includes(err)))


def get_compiler_target(parseLogOptions, compiler):
    """
    Returns the target triple of the given compiler as a string.
    """
    err = ""
    if parseLogOptions.compiler_target_file is None:
        cmd = compiler + ' -v'
        LOG.debug("Retrieving target platform information via '" + cmd + "'")
        err = get_compiler_err(cmd)
    else:
        err = load_compiler_info(parseLogOptions.compiler_target_file,
                                 compiler,
                                 'target')

    if parseLogOptions.output_path is not None:
        dump_compiler_info(compiler_info_dump_file,
                           compiler,
                           'target',
                           err)
    return parse_compiler_target(err)


def get_compiler_standard(parseLogOptions, compiler, lang):
    """
    Returns the default compiler standard of the given compiler. The standard
    is determined by the values of __STDC_VERSION__ and __cplusplus predefined
    macros. These values are integers indicating the date of the standard.
    However, GCC supports a GNU extension for each standard. For sake of
    generality we return the GNU extended standard, since it should be a
    superset of the non-extended one, thus applicable in a more general manner.
    """
    VERSION_C = u"""
#ifdef __STDC_VERSION__
#  if __STDC_VERSION__ >= 201710L
#    error CC_FOUND_STANDARD_VER#17
#  elif __STDC_VERSION__ >= 201112L
#    error CC_FOUND_STANDARD_VER#11
#  elif __STDC_VERSION__ >= 199901L
#    error CC_FOUND_STANDARD_VER#99
#  elif __STDC_VERSION__ >= 199409L
#    error CC_FOUND_STANDARD_VER#94
#  else
#    error CC_FOUND_STANDARD_VER#90
#  endif
#else
#  error CC_FOUND_STANDARD_VER#90
#endif
    """

    VERSION_CPP = u"""
#ifdef __cplusplus
#  if __cplusplus >= 201703L
#    error CC_FOUND_STANDARD_VER#17
#  elif __cplusplus >= 201402L
#    error CC_FOUND_STANDARD_VER#14
#  elif __cplusplus >= 201103L
#    error CC_FOUND_STANDARD_VER#11
#  elif __cplusplus >= 199711L
#    error CC_FOUND_STANDARD_VER#98
#  else
#    error CC_FOUND_STANDARD_VER#98
#  endif
#else
#  error CC_FOUND_STANDARD_VER#98
#endif
    """

    standard = ""
    if parseLogOptions.compiler_info_file is None:
        with tempfile.NamedTemporaryFile(
                suffix=('.c' if lang == 'c' else '.cpp')) as source:

            with source.file as f:
                f.write(VERSION_C if lang == 'c' else VERSION_CPP)

            try:
                proc = subprocess.Popen([compiler, source.name],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                _, err = proc.communicate()  # Wait for execution.

                finding = re.search('CC_FOUND_STANDARD_VER#(.+)', err)

                if finding:
                    standard = finding.group(1)
            except OSError:
                LOG.error("Error during the compilation of compiler standard "
                          "detector.")

        if standard:
            if standard == '94':
                # Special case for C94 standard.
                standard = '-std=iso9899:199409'
            else:
                standard = \
                    '-std=gnu' + ('' if lang == 'c' else '++') + standard
    else:
        standard = load_compiler_info(parseLogOptions.compiler_info_file,
                                      compiler,
                                      'default_standard')

    if parseLogOptions.output_path is not None and standard:
        dump_compiler_info(compiler_info_dump_file,
                           compiler,
                           'default_standard',
                           standard)

    return standard


def parse_compile_commands_json(log_data, parseLogOptions):
    """
    log_data: content of a compile command json.
    """

    output_path = parseLogOptions.output_path
    if output_path is not None:
        global compiler_info_dump_file
        compiler_info_dump_file = os.path.join(output_path,
                                               compiler_info_dump_file)
        remove_file_if_exists(compiler_info_dump_file)

    actions = []
    filtered_build_actions = {}

    compiler_includes = {}
    compiler_target = {}
    compiler_standard = {}

    counter = 0
    for entry in log_data:
        sourcefile = entry['file']

        if not os.path.isabs(sourcefile):
            # Newest versions of intercept-build can create the 'file' in the
            # JSON Compilation Database as a relative path.
            sourcefile = os.path.join(os.path.abspath(entry['directory']),
                                      sourcefile)

        lang = option_parser.get_language(sourcefile[sourcefile.rfind('.'):])

        if not lang:
            continue

        action = build_action.BuildAction(counter)
        if 'command' in entry:
            command = entry['command']

            # Old versions of intercept-build (confirmed to those shipping
            # with upstream clang-5.0) do escapes in another way:
            # -DVARIABLE="a b" becomes -DVARIABLE=\"a b\" in the output.
            # This would be messed up later on by options_parser, so need a
            # fix here. (Should be removed once we are sure noone uses this
            # intercept-build anymore!)
            if r'\"' in command:
                command = command.replace(r'\"', '"')
        elif 'arguments' in entry:
            # Newest versions of intercept-build create an argument vector
            # instead of a command string.
            command = ' '.join(entry['arguments'])
        else:
            raise KeyError("No valid 'command' or 'arguments' entry found!")
        results = option_parser.parse_options(command)

        action.original_command = command

        # If the original include directory could not be found
        # in the filesystem, it is possible that it was provided
        # relative to the working directory in the compile json.
        compile_opts = results.compile_opts
        for i, opt in enumerate(compile_opts):
            if opt.startswith('-I'):
                inc_dir = opt[2:].strip()
                if not os.path.isdir(inc_dir):
                    compile_opts[i] = '-I' + \
                        os.path.join(entry['directory'], inc_dir)

        action.analyzer_options = compile_opts

        action.lang = results.lang
        action.target = results.arch
        action.output = results.output

        add_compiler_defaults = True

        # With gcc-toolchain a non default compiler toolchain can be set.
        # Clang will search for include paths and libraries based on the
        # gcc-toolchain parameter.
        # Detecting extra include paths from the host compiler could
        # conflict with this.

        # For example if the compiler in the compile command is clang
        # and gcc-toolchain is set we will get the include paths
        # for clang and not for the compiler set in gcc-toolchain.
        # This can cause missing headers during the analysis.

        toolchain = gcc_toolchain.toolchain_in_args(action.analyzer_options)
        if toolchain:
            add_compiler_defaults = False

        # Store the compiler built in include paths and defines.
        if add_compiler_defaults and results.compiler:
            if not (results.compiler in compiler_includes):
                # Fetch defaults from the compiler,
                # make sure we use the correct architecture.
                extra_opts = []
                for regex in COMPILE_OPTS_FWD_TO_DEFAULTS_GETTER:
                    pattern = re.compile(regex)
                    for comp_opt in action.analyzer_options:
                        if re.match(pattern, comp_opt):
                            extra_opts.append(comp_opt)

                compiler_includes[results.compiler] = \
                    get_compiler_includes(parseLogOptions, results.compiler,
                                          results.lang, results.compile_opts,
                                          extra_opts)

            if not (results.compiler in compiler_target):
                compiler_target[results.compiler] = \
                    get_compiler_target(parseLogOptions, results.compiler)

            if not (results.compiler in compiler_standard):
                compiler_standard[results.compiler] = \
                    get_compiler_standard(parseLogOptions, results.compiler,
                                          results.lang)

            action.compiler_includes = compiler_includes[results.compiler]
            action.compiler_standard = compiler_standard[results.compiler]
            action.target = compiler_target[results.compiler]

        if results.action != option_parser.ActionType.COMPILE:
            continue

        # TODO: Check arch.
        action.directory = entry['directory']
        action.sources = sourcefile
        # Filter out duplicate compilation commands.
        unique_key = action.cmp_key
        if filtered_build_actions.get(unique_key) is None:
            filtered_build_actions[unique_key] = action

        del action
        counter += 1

    for _, ba in filtered_build_actions.items():
        actions.append(ba)
    return actions


def parse_log(logfilepath, parseLogOptions):
    """
    logfilepath: the compile command json file which should be parsed.
    """
    LOG.debug('Parsing log file: ' + logfilepath)

    try:
        data = load_json_or_empty(logfilepath, {})
        actions = parse_compile_commands_json(data, parseLogOptions)
    except (ValueError, KeyError, TypeError) as ex:
        if os.stat(logfilepath).st_size == 0:
            LOG.error('The compile database is empty.')
        else:
            LOG.error('The compile database is not valid.')
        LOG.debug(traceback.format_exc())
        LOG.debug(ex)
        sys.exit(1)

    LOG.debug('Parsing log file done.')

    return actions
