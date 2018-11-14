# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from __future__ import print_function
from __future__ import absolute_import

from collections import defaultdict
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
from libcodechecker.log.build_action import BuildAction
from libcodechecker.logger import get_logger

LOG = get_logger('buildlogger')


# Replace gcc/g++ build target options with values accepted by Clang.
REPLACE_OPTIONS_MAP = {
    '-mips32': ['-target', 'mips', '-mips32'],
    '-mips64': ['-target', 'mips64', '-mips64'],
    '-mpowerpc': ['-target', 'powerpc'],
    '-mpowerpc64': ['-target', 'powerpc64']
}


# The compilation flags of which the prefix is any of these regular expressions
# will not be included in the output Clang command.
IGNORED_OPTIONS = [
    # --- UNKNOWN BY CLANG --- #
    '-fallow-fetchr-insn',
    '-fcall-saved-',
    '-fcond-mismatch',
    '-fconserve-stack',
    '-fcrossjumping',
    '-fcse-follow-jumps',
    '-fcse-skip-blocks',
    '-ffixed-r2',
    '-ffp$',
    '-fgcse-lm',
    '-fhoist-adjacent-loads',
    '-findirect-inlining',
    '-finline-limit',
    '-finline-local-initialisers',
    '-fipa-sra',
    '-fno-aggressive-loop-optimizations',
    '-fno-delete-null-pointer-checks',
    '-fno-jump-table',
    '-fno-strength-reduce',
    '-fno-toplevel-reorder',
    '-fno-unit-at-a-time',
    '-fno-var-tracking-assignments',
    '-fobjc-link-runtime',
    '-fpartial-inlining',
    '-fpeephole2',
    '-fr$',
    '-fregmove',
    '-frename-registers',
    '-freorder-functions',
    '-frerun-cse-after-loop',
    '-fs$',
    '-fsched-spec',
    '-fthread-jumps',
    '-ftree-pre',
    '-ftree-switch-conversion',
    '-ftree-tail-merge',
    '-m(no-)?abm',
    '-m(no-)?sdata',
    '-m(no-)?spe',
    '-m(no-)?string$',
    '-m(no-)?dsbt',
    '-m(no-)?fixed-ssp',
    '-m(no-)?pointers-to-nested-functions',
    '-mpcrel-func-addr',
    '-maccumulate-outgoing-args',
    '-mcall-aixdesc',
    '-mppa3-addr-bug',
    '-mtraceback=',
    '-mtext=',
    '-misa=',
    '-mfix-cortex-m3-ldrd$',
    '-mmultiple$',
    '-msahf$',
    '-mthumb-interwork$',
    '-mupdate$',

    # Deprecated ARM specific option
    # to Generate a stack frame that is compliant
    # with the ARM Procedure Call Standard.
    '-mapcs',
    '-fno-merge-const-bfstores$',
    '-fno-ipa-sra$',
    '-mno-thumb-interwork$',
    # ARM specific option.
    # Prevent the reordering of
    # instructions in the function prologue.
    '-mno-sched-prolog',
    # This is not unknown but we want to preserve asserts to improve the
    # quality of analysis.
    '-DNDEBUG$',

    # --- IGNORED --- #
    '-save-temps',
    # Clang gives different warnings than GCC. Thus if these flags are kept,
    # '-Werror', '-pedantic-errors' the analysis with Clang can fail even
    # if the compilation passes with GCC.
    '-Werror',
    '-pedantic-errors',
    '-g(.+)?$',
    # Link Time Optimization:
    '-flto',
    # MicroBlaze Options:
    '-mxl',
    # PowerPC SPE Options:
    '-mfloat-gprs',
    '-mabi'
]

IGNORED_OPTIONS = re.compile('|'.join(IGNORED_OPTIONS))


# The compilation flags of which the prefix is any of these regular expressions
# will not be included in the output Clang command. These flags have further
# parameters which are also omitted. The number of parameters is indicated in
# this dictionary.
IGNORED_PARAM_OPTIONS = {
    re.compile('-install_name'): 1,
    re.compile('-exported_symbols_list'): 1,
    re.compile('-current_version'): 1,
    re.compile('-compatibility_version'): 1,
    re.compile('-init$'): 1,
    re.compile('-e$'): 1,
    re.compile('-seg1addr'): 1,
    re.compile('-bundle_loader'): 1,
    re.compile('-multiply_defined'): 1,
    re.compile('-sectorder'): 3,
    re.compile('--param$'): 1,
    re.compile('-u$'): 1,
    re.compile('--serialize-diagnostics'): 1,
    re.compile('-framework'): 1,
    # Skip paired Xclang options like "-Xclang -mllvm".
    re.compile('-Xclang'): 1,
    # Darwin linker can be given a file with lists the sources for linking.
    re.compile('-filelist'): 1
}


COMPILE_OPTIONS = [
    '-nostdinc',
    r'-nostdinc\+\+',
    '-pedantic',
    '-O[1-3]',
    '-Os',
    '-std=',
    '-f',
    '-m',
    '-Wno-',
    '--sysroot=',
    '--gcc-toolchain='
]

COMPILE_OPTIONS = re.compile('|'.join(COMPILE_OPTIONS))


COMPILE_OPTIONS_MERGED = [
    '--sysroot',
    '--include',
    '-include',
    '-iquote',
    '-[DIUF]',
    '-idirafter',
    '-isystem',
    '-macros',
    '-isysroot',
    '-iprefix',
    '-iwithprefix',
    '-iwithprefixbefore'
]

COMPILE_OPTIONS_MERGED = \
    re.compile('(' + '|'.join(COMPILE_OPTIONS_MERGED) + ')')


PRECOMPILATION_OPTION = re.compile('-(E|M[T|Q|F|J|P|V|M]*)$')


class ImplicitCompilerInfo(object):
    """
    This class helps to fetch and set some additional compiler flags which are
    implicitly added when using GCC.
    """
    # TODO: These dicts are mapping compiler to the corresponding information.
    # It may not be enough to use the compiler as a key, because the implicit
    # information depends on other data like language or target architecture.
    compiler_includes = {}
    compiler_target = {}
    compiler_standard = {}

    def __get_compiler_err(self, cmd):
        """
        Returns the stderr of a compiler invocation as string.
        """
        try:
            LOG.debug("Retrieving default includes via '" + cmd + "'")
            proc = subprocess.Popen(shlex.split(cmd),
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

            _, err = proc.communicate("")
            return err
        except OSError as oerr:
            LOG.error("Error during process execution: " + cmd + '\n' +
                      oerr.strerror + "\n")

    def __parse_compiler_includes(self, lines):
        """
        Parse the compiler include paths from a string
        """
        start_mark = "#include <...> search starts here:"
        end_mark = "End of search list."

        include_paths = []

        do_append = False
        for line in lines.splitlines():
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
                    include_paths.append(line[:fpos - 1])

            if line.startswith(start_mark):
                do_append = True

        return include_paths

    def __filter_compiler_includes(self, include_dirs):
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
            if os.path.basename(
                    os.path.normpath(include_dir)) == "include-fixed":
                continue
            if contains_intrinsic_headers(include_dir):
                continue
            result.append(include_dir)
        return result

    def get_compiler_includes(self, action):
        """
        Returns a list of default includes of the given compiler.

        action -- A BuildAction object containing the details of compilation.
        """
        # The first sysroot flag found among the compilation options is added
        # to the command below to give a more precise default include list.
        # Absence of any sysroot flags results in an empty string.
        sysroot = ""
        for i, item in enumerate(action.analyzer_options):
            if item.startswith("--sysroot"):
                # len("--sysroot") == 9
                # len("--sysroot=") == 10
                sysroot = action.analyzer_options[i + 1] \
                    if len(item) == 9 else item[10:]
                sysroot = "--sysroot=" + sysroot

        # If these options are present in the original build command, they must
        # be forwarded to get_compiler_includes and get_compiler_defines so the
        # resulting includes point to the target that was used in the build.
        pattern = re.compile('-m(32|64)|-std=')
        extra_opts = filter(pattern.match, action.analyzer_options)
        cmd = action.compiler + " " + ' '.join(extra_opts) \
            + " -E -x " + action.lang + " " + sysroot + " - -v "

        include_dirs = self.__filter_compiler_includes(
            self.__parse_compiler_includes(self.__get_compiler_err(cmd)))

        return ["-isystem " + os.path.normpath(idir) for idir in include_dirs]

    def get_compiler_target(self, action):
        """
        Returns the target triple of the given compiler as a string.

        action -- A BuildAction object containing the details of compilation.
        """
        lines = self.__get_compiler_err(action.compiler + ' -v')

        target_label = "Target:"
        target = ""

        for line in lines.splitlines(True):
            line = line.strip().split()
            if len(line) > 1 and line[0] == target_label:
                target = line[1]

        return target

    def get_compiler_standard(self, action):
        """
        Returns the default compiler standard of the given compiler. The
        standard is determined by the values of __STDC_VERSION__ and
        __cplusplus predefined macros. These values are integers indicating the
        date of the standard. However, GCC supports a GNU extension for each
        standard. For sake of generality we return the GNU extended standard,
        since it should be a superset of the non-extended one, thus applicable
        in a more general manner.
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
        with tempfile.NamedTemporaryFile(
                suffix=('.c' if action.lang == 'c' else '.cpp')) as source:

            with source.file as f:
                f.write(VERSION_C if action.lang == 'c' else VERSION_CPP)

            try:
                proc = subprocess.Popen([action.compiler, source.name],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                _, err = proc.communicate()  # Wait for execution.

                finding = re.search('CC_FOUND_STANDARD_VER#(.+)', err)

                if finding:
                    standard = finding.group(1)
            except OSError:
                LOG.error("Error during the compilation of compiler "
                          "standard detector.")

        if standard:
            if standard == '94':
                # Special case for C94 standard.
                standard = '-std=iso9899:199409'
            else:
                standard = '-std=gnu' \
                         + ('' if action.lang == 'c' else '++') \
                         + standard

        return standard

    def set_implicit_compiler_info(self, action):
        if action.compiler not in self.compiler_includes:
            self.compiler_includes[action.compiler] = \
                self.get_compiler_includes(action)
        if action.compiler not in self.compiler_target:
            self.compiler_target[action.compiler] = \
                self.get_compiler_target(action)
        if action.compiler not in self.compiler_standard:
            self.compiler_standard[action.compiler] = \
                self.get_compiler_standard(action)

        action.compiler_includes = self.compiler_includes[action.compiler]
        action.compiler_standard = self.compiler_standard[action.compiler]
        action.target = self.compiler_target[action.compiler]

    def get_implicit_compiler_info(self):
        result = defaultdict(dict)

        for compiler, includes in self.compiler_includes.items():
            result[compiler]['includes'] = includes
        for compiler, target in self.compiler_target.items():
            result[compiler]['target'] = target
        for compiler, standard in self.compiler_standard.items():
            result[compiler]['default_standard'] = standard

        return result


class OptionIterator(object):
    def __init__(self, args):
        self._item = None
        self._it = iter(args)

    def next(self):
        self._item = next(self._it)
        return self

    def __iter__(self):
        return self

    @property
    def item(self):
        return self._item


def get_language(extension):
    # TODO: There are even more in the man page of gcc.
    mapping = {'.c': 'c',
               '.cp': 'c++',
               '.cpp': 'c++',
               '.cxx': 'c++',
               '.txx': 'c++',
               '.cc': 'c++',
               '.C': 'c++',
               '.ii': 'c++',
               '.m': 'objective-c',
               '.mm': 'objective-c++'}
    return mapping.get(extension)


def __collect_compile_opts(flag_iterator, buildaction):
    """
    This function collects the compilation (i.e. not linker or preprocessor)
    flags to the buildaction.
    """
    if COMPILE_OPTIONS.match(flag_iterator.item):
        buildaction.analyzer_options.append(flag_iterator.item)
        return True

    m = COMPILE_OPTIONS_MERGED.match(flag_iterator.item)

    if m:
        flag = m.group(0)
        together = len(flag) != len(flag_iterator.item)

        if together:
            param = flag_iterator.item[len(flag):]
        else:
            next(flag_iterator)
            param = flag_iterator.item

        if flag == '-I':
            param = os.path.normpath(
                os.path.join(buildaction.directory, param))

        if together:
            buildaction.analyzer_options.append(flag + param)
        else:
            buildaction.analyzer_options.extend([flag, param])

        return True

    return False


def __skip_sources(flag_iterator, _):
    """
    This function skips the compiled source file names (i.e. the arguments
    which don't start with a dash character).
    """
    if flag_iterator.item[0] != '-':
        return True

    return False


def __determine_action_type(flag_iterator, buildaction):
    """
    This function determines whether this is a preprocessing, compilation or
    linking action and sets it in the buildaction object.
    """
    if flag_iterator.item == '-c':
        buildaction.action_type = BuildAction.COMPILE
        return True
    elif flag_iterator.item.startswith('-print-prog-name'):
        buildaction.action_type = BuildAction.INFO
        return True
    elif PRECOMPILATION_OPTION.match(flag_iterator.item):
        buildaction.action_type = BuildAction.PREPROCESS
        return True

    return False


def __get_arch(flag_iterator, buildaction):
    """
    This function consumes -arch flag which is followed by the target
    architecture. This is then collected to the buildaction object.
    """
    # TODO: Is this really a target architecture? Have we seen this flag being
    # used in a real project? This -arch flag is not really documented among
    # GCC flags.
    # Where do we use this architecture during analysis and why?
    if flag_iterator.item == '-arch':
        next(flag_iterator)
        buildaction.target = flag_iterator.item
        return True

    return False


def __get_language(flag_iterator, buildaction):
    """
    This function consumes -x flag which is followed by the language. This
    language is then collected to the buildaction object.
    """
    # TODO: Known issue: a -x flag may precede all source files in the build
    # command with different languages.
    if flag_iterator.item == '-x':
        next(flag_iterator)
        buildaction.lang = flag_iterator.item
        return True

    return False


def __get_output(flag_iterator, buildaction):
    """
    This function consumes -o flag which is followed by the output file of the
    action. This file is then collected to the buildaction object.
    """
    if flag_iterator.item == '-o':
        next(flag_iterator)
        buildaction.output = flag_iterator.item
        return True

    return False


def __replace(flag_iterator, buildaction):
    """
    This function extends the analyzer options list with the corresponding
    replacement based on REPLACE_OPTIONS_MAP if the flag_iterator is currently
    pointing to a flag to replace.
    """
    value = REPLACE_OPTIONS_MAP.get(flag_iterator.item)

    if value:
        buildaction.analyzer_options.extend(value)

    return bool(value)


def __skip(flag_iterator, _):
    """
    This function skips the flag pointed by the given flag_iterator with its
    parameters if any.
    """
    if IGNORED_OPTIONS.match(flag_iterator.item):
        return True

    for pattern, arg_num in IGNORED_PARAM_OPTIONS.items():
        if pattern.match(flag_iterator.item):
            for _ in range(arg_num):
                next(flag_iterator)
            return True

    return False


def parse_options(compilation_db_entry):
    """
    This function parses a GCC compilation action and returns a BuildAction
    object which can be the input of Clang analyzer tools.

    compilation_db_entry -- An entry from a valid compilation database JSON
                            file, i.e. a dictionary with the compilation
                            command, the compiled file and the current working
                            directory.
    """

    buildaction = BuildAction()

    if 'arguments' in compilation_db_entry:
        gcc_command = compilation_db_entry['arguments']
        buildaction.original_command = ' '.join(gcc_command)
    elif 'command' in compilation_db_entry:
        buildaction.original_command = compilation_db_entry['command']
        gcc_command = compilation_db_entry['command'] \
            .replace(r'\"', '"') \
            .replace(r'"', r'"\"')
        gcc_command = shlex.split(gcc_command)
    else:
        raise KeyError("No valid 'command' or 'arguments' entry found!")

    buildaction.directory = compilation_db_entry['directory']
    buildaction.action_type = buildaction.COMPILE
    buildaction.compiler = gcc_command[0]
    if '++' in buildaction.compiler or 'cpp' in buildaction.compiler:
        buildaction.lang = 'c++'

    flag_transformers = [
        __skip,
        __collect_compile_opts,
        __determine_action_type,
        __replace,
        __skip_sources,
        __get_arch,
        __get_language,
        __get_output]

    for it in OptionIterator(gcc_command[1:]):
        for flag_transformer in flag_transformers:
            if flag_transformer(it, buildaction):
                break
        else:
            pass
            # print('Unhandled argument: ' + it.item)

    buildaction.source = os.path.normpath(
        os.path.join(compilation_db_entry['directory'],
                     compilation_db_entry['file']))

    # In case the file attribute in the entry is empty.
    if buildaction.source == '.':
        buildaction.source = ''

    lang = get_language(os.path.splitext(buildaction.source)[1])
    if lang:
        if buildaction.lang is None:
            buildaction.lang = lang
    else:
        buildaction.action_type = BuildAction.LINK

    return buildaction


def parse_log(compilation_database,
              skip_handler=None,
              compiler_info_file=None):
    """
    compilation_database -- A compilation database as a list of dict objects.
                            These object should contain "file", "dictionary"
                            and "command" keys. The "command" may be replaced
                            by "arguments" which is a split command. Older
                            versions of intercept-build provide the build
                            command this way.
    skip_handler -- A SkipListHandler object which helps to skip build actions
                    that shouldn't be analyzed. The build actions described by
                    this handler will not be the part of the result list.
    compiler_info_file -- An optional filename where implicit compiler data
                          is dumped (implicit include paths, architecture
                          targets, default standard version).
    """
    try:
        filtered_build_actions = set()
        implicit_compiler_info = ImplicitCompilerInfo()

        for entry in compilation_database:
            if skip_handler and skip_handler.should_skip(entry['file']):
                continue

            action = parse_options(entry)

            if not action.lang:
                continue
            if action.action_type != build_action.BuildAction.COMPILE:
                continue

            # With gcc-toolchain a non default compiler toolchain can be set.
            # Clang will search for include paths and libraries based on the
            # gcc-toolchain parameter.
            # Detecting extra include paths from the host compiler could
            # conflict with this.

            # For example if the compiler in the compile command is clang
            # and gcc-toolchain is set we will get the include paths
            # for clang and not for the compiler set in gcc-toolchain.
            # This can cause missing headers during the analysis.

            toolchain = \
                gcc_toolchain.toolchain_in_args(action.analyzer_options)

            # Store the compiler built in include paths and defines.
            if not toolchain:
                implicit_compiler_info.set_implicit_compiler_info(action)

            # Filter out duplicate compilation commands.
            filtered_build_actions.add(action)

        if compiler_info_file:
            with open(compiler_info_file, 'w') as f:
                json.dump(implicit_compiler_info.get_implicit_compiler_info(),
                          f)

        return list(filtered_build_actions)
    except (ValueError, KeyError, TypeError) as ex:
        if os.stat(logfilepath).st_size == 0:
            LOG.error('The compile database is empty.')
        else:
            LOG.error('The compile database is not valid.')
        LOG.debug(traceback.format_exc())
        LOG.debug(ex)
        sys.exit(1)

    LOG.debug('Parsing log file done.')
