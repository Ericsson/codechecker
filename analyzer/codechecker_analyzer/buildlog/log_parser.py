# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from __future__ import print_function
from __future__ import absolute_import

from collections import defaultdict
from distutils.spawn import find_executable
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import traceback

from codechecker_common.logger import get_logger
from codechecker_common.util import load_json_or_empty

from .. import gcc_toolchain
from .build_action import BuildAction

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

# These flag groups are ignored together.
# TODO: This list is not used yet, but will be applied in the next release.
IGNORED_FLAG_LISTS = [
  ['-Xclang', '-mllvm'],
  ['-Xclang', '-emit-llvm'],
  ['-Xclang', '-instcombine-lower-dbg-declare=0']
]

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
    compiler_isexecutable = {}

    @staticmethod
    def is_executable_compiler(compiler):
        if compiler not in ImplicitCompilerInfo.compiler_isexecutable:
            ImplicitCompilerInfo.compiler_isexecutable[compiler] = \
                find_executable(compiler) is not None

        return ImplicitCompilerInfo.compiler_isexecutable[compiler]

    @staticmethod
    def __get_compiler_err(cmd):
        """
        Returns the stderr of a compiler invocation as string
        or None in case of error.
        """
        try:
            LOG.debug("Retrieving default includes via '" + cmd + "'")
            proc = subprocess.Popen(shlex.split(cmd),
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True)

            _, err = proc.communicate("")
            return err
        except OSError as oerr:
            LOG.error("Error during process execution: " + cmd + '\n' +
                      oerr.strerror + "\n")

    @staticmethod
    def __parse_compiler_includes(lines):
        """
        Parse the compiler include paths from a string
        """
        start_mark = "#include <...> search starts here:"
        end_mark = "End of search list."

        include_paths = []

        if not lines:
            return include_paths

        do_append = False
        for line in lines.splitlines():
            if line.startswith(end_mark):
                break
            if do_append:
                line = line.strip()
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

    @staticmethod
    def __filter_compiler_includes(include_dirs):
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

    @staticmethod
    def get_compiler_includes(compiler, language, compiler_flags):
        """
        Returns a list of default includes of the given compiler.

        compiler -- The compiler binary of which the implicit include paths are
                    fetched.
        language -- The programming language being compiled (e.g. 'c' or 'c++')
        compiler_flags -- A list of compiler flags which may affect the list
                          of implicit compiler include paths, like -std=,
                          --sysroot= or -m32, -m64.
        """
        # If these options are present in the original build command, they must
        # be forwarded to get_compiler_includes and get_compiler_defines so the
        # resulting includes point to the target that was used in the build.
        pattern = re.compile('-m(32|64)|-std=')
        extra_opts = filter(pattern.match, compiler_flags)

        pos = next((pos for pos, val in enumerate(compiler_flags)
                    if val.startswith('--sysroot')), None)
        if pos is not None:
            if compiler_flags[pos] == '--sysroot':
                extra_opts.append('--sysroot=' + compiler_flags[pos + 1])
            else:
                extra_opts.append(compiler_flags[pos])

        cmd = compiler + " " + ' '.join(extra_opts) \
            + " -E -x " + language + " - -v "

        ICI = ImplicitCompilerInfo
        include_dirs = ICI.__filter_compiler_includes(
            ICI.__parse_compiler_includes(ICI.__get_compiler_err(cmd)))
        idirs = []
        for idir in include_dirs:
            idirs.append("-isystem")
            idirs.append(os.path.normpath(idir))
        return idirs

    @staticmethod
    def get_compiler_target(compiler):
        """
        Returns the target triple of the given compiler as a string.

        compiler -- The compiler binary of which the target architecture is
                    fetched.
        """
        lines = ImplicitCompilerInfo.__get_compiler_err(compiler + ' -v')

        if lines is None:
            return ""

        target_label = "Target:"
        target = ""

        for line in lines.splitlines(True):
            line = line.strip().split()
            if len(line) > 1 and line[0] == target_label:
                target = line[1]

        return target

    @staticmethod
    def get_compiler_standard(compiler, language):
        """
        Returns the default compiler standard of the given compiler. The
        standard is determined by the values of __STDC_VERSION__ and
        __cplusplus predefined macros. These values are integers indicating the
        date of the standard. However, GCC supports a GNU extension for each
        standard. For sake of generality we return the GNU extended standard,
        since it should be a superset of the non-extended one, thus applicable
        in a more general manner.

        compiler -- The compiler binary of which the default compiler standard
                    is fetched.
        language -- The programming lenguage being compiled (e.g. 'c' or 'c++')
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
                mode='w+',
                suffix=('.c' if language == 'c' else '.cpp')) as source:

            with source.file as f:
                f.write(VERSION_C if language == 'c' else VERSION_CPP)

            err = ImplicitCompilerInfo.\
                __get_compiler_err(" ".join([compiler, source.name]))

            if err is not None:
                finding = re.search('CC_FOUND_STANDARD_VER#(.+)', err)
                if finding:
                    standard = finding.group(1)

        if standard:
            if standard == '94':
                # Special case for C94 standard.
                standard = '-std=iso9899:199409'
            else:
                standard = '-std=gnu' \
                    + ('' if language == 'c' else '++') \
                    + standard

        return standard

    @staticmethod
    def load_compiler_info(filename, compiler):
        contents = load_json_or_empty(filename, {})
        compiler_info = contents.get(compiler)
        if compiler_info is None:
            LOG.error("Could not find compiler %s in file %s",
                      compiler, filename)

        ICI = ImplicitCompilerInfo
        ICI.compiler_includes[compiler] = []
        for element in map(shlex.split, compiler_info.get('includes')):
            ICI.compiler_includes[compiler].extend(element)
        ICI.compiler_standard[compiler] = compiler_info.get('default_standard')
        ICI.compiler_target[compiler] = compiler_info.get('target')

    @staticmethod
    def set(details, compiler_info_file=None):
        ICI = ImplicitCompilerInfo

        if compiler_info_file and os.path.exists(compiler_info_file):
            # Compiler info file exists, load it.
            ICI.load_compiler_info(compiler_info_file, details['compiler'])
        else:
            # Invoke compiler to gather implicit compiler info.
            if details['compiler'] not in ICI.compiler_includes:
                ICI.compiler_includes[details['compiler']] = \
                    ICI.get_compiler_includes(details['compiler'],
                                              details['lang'],
                                              details['analyzer_options'])
            if details['compiler'] not in ICI.compiler_standard:
                ICI.compiler_standard[details['compiler']] = \
                    ICI.get_compiler_standard(details['compiler'],
                                              details['lang'])
            if details['compiler'] not in ICI.compiler_target:
                ICI.compiler_target[details['compiler']] = \
                    ICI.get_compiler_target(details['compiler'])

        details['compiler_includes'] = details['compiler_includes'] or \
            ICI.compiler_includes[details['compiler']]
        details['compiler_standard'] = details['compiler_standard'] or \
            ICI.compiler_standard[details['compiler']]
        details['target'] = details['target'] or \
            ICI.compiler_target[details['compiler']]

    @staticmethod
    def get():
        ICI = ImplicitCompilerInfo

        result = defaultdict(dict)
        for compiler, includes in ICI.compiler_includes.items():
            result[compiler]['includes'] = includes
        for compiler, target in ICI.compiler_target.items():
            result[compiler]['target'] = target
        for compiler, standard in ICI.compiler_standard.items():
            result[compiler]['default_standard'] = standard

        return result


class OptionIterator(object):

    def __init__(self, args):
        self._item = None
        self._it = iter(args)

    def __next__(self):
        self._item = next(self._it)
        return self

    next = __next__

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


def determine_compiler(gcc_command):
    """
    This function determines the compiler from the given compilation command.
    If the first part of the gcc_command is ccache invocation then the rest
    should be a complete compilation command.

    CCache may have two forms:
    1. ccache g++ main.cpp
    2. ccache main.cpp
    In the first case this function drops "ccache" from gcc_command and returns
    the next compiler name.
    In the second case the compiler can be given by config files or an
    environment variable. Currently we don't handle this version, and in this
    case the compiler remanis "ccache" and the gcc_command is not changed.
    The two cases are distinguished by checking whether the second parameter is
    an executable or not.

    gcc_command -- A split build action as a list which may or may not start
                   with ccache.

    TODO: The second case could be handled if there was a way for querying the
    used compiler from ccache. This can be configured for ccache in config
    files or environment variables.
    """
    if 'ccache' in gcc_command[0]:
        if ImplicitCompilerInfo.is_executable_compiler(gcc_command[1]):
            return gcc_command[1]

    return gcc_command[0]


def __collect_compile_opts(flag_iterator, details):
    """
    This function collects the compilation (i.e. not linker or preprocessor)
    flags to the buildaction.
    """
    if COMPILE_OPTIONS.match(flag_iterator.item):
        details['analyzer_options'].append(flag_iterator.item)
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
                os.path.join(details['directory'], param))

        if together:
            details['analyzer_options'].append(flag + param)
        else:
            details['analyzer_options'].extend([flag, param])

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


def __determine_action_type(flag_iterator, details):
    """
    This function determines whether this is a preprocessing, compilation or
    linking action and sets it in the buildaction object. If the action type is
    set to COMPILE earlier then we don't set it to anything else.
    """
    if flag_iterator.item == '-c':
        details['action_type'] = BuildAction.COMPILE
        return True
    elif flag_iterator.item.startswith('-print-prog-name'):
        if details['action_type'] != BuildAction.COMPILE:
            details['action_type'] = BuildAction.INFO
        return True
    elif PRECOMPILATION_OPTION.match(flag_iterator.item):
        if details['action_type'] != BuildAction.COMPILE:
            details['action_type'] = BuildAction.PREPROCESS
        return True

    return False


def __get_arch(flag_iterator, details):
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
        details['target'] = flag_iterator.item
        return True

    return False


def __get_language(flag_iterator, details):
    """
    This function consumes -x flag which is followed by the language. This
    language is then collected to the buildaction object.
    """
    # TODO: Known issue: a -x flag may precede all source files in the build
    # command with different languages.
    if flag_iterator.item.startswith('-x'):
        if flag_iterator.item == '-x':
            next(flag_iterator)
            details['lang'] = flag_iterator.item
        else:
            details['lang'] = flag_iterator.item[2:]  # 2 == len('-x')
        return True
    return False


def __get_output(flag_iterator, details):
    """
    This function consumes -o flag which is followed by the output file of the
    action. This file is then collected to the buildaction object.
    """
    if flag_iterator.item == '-o':
        next(flag_iterator)
        details['output'] = flag_iterator.item
        return True

    return False


def __replace(flag_iterator, details):
    """
    This function extends the analyzer options list with the corresponding
    replacement based on REPLACE_OPTIONS_MAP if the flag_iterator is currently
    pointing to a flag to replace.
    """
    value = REPLACE_OPTIONS_MAP.get(flag_iterator.item)

    if value:
        details['analyzer_options'].extend(value)

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


def parse_options(compilation_db_entry, compiler_info_file=None):
    """
    This function parses a GCC compilation action and returns a BuildAction
    object which can be the input of Clang analyzer tools.

    compilation_db_entry -- An entry from a valid compilation database JSON
                            file, i.e. a dictionary with the compilation
                            command, the compiled file and the current working
                            directory.
    compiler_info_file -- Contains the path to a compiler info file.
    """

    details = {
        'analyzer_options': [],
        'compiler_includes': [],
        'compiler_standard': '',
        'analyzer_type': -1,
        'original_command': '',
        'directory': '',
        'output': '',
        'lang': None,
        'target': '',
        'source': ''}

    if 'arguments' in compilation_db_entry:
        gcc_command = compilation_db_entry['arguments']
        details['original_command'] = ' '.join(gcc_command)
    elif 'command' in compilation_db_entry:
        details['original_command'] = compilation_db_entry['command']
        gcc_command = shlex.split(compilation_db_entry['command'])
    else:
        raise KeyError("No valid 'command' or 'arguments' entry found!")

    details['directory'] = compilation_db_entry['directory']
    details['action_type'] = None
    details['compiler'] = determine_compiler(gcc_command)
    if '++' in details['compiler'] or 'cpp' in details['compiler']:
        details['lang'] = 'c++'

    flag_transformers = [
        __skip,
        __replace,
        __collect_compile_opts,
        __determine_action_type,
        __skip_sources,
        __get_arch,
        __get_language,
        __get_output]

    for it in OptionIterator(gcc_command[1:]):
        for flag_transformer in flag_transformers:
            if flag_transformer(it, details):
                break
        else:
            pass
            # print('Unhandled argument: ' + it.item)

    if details['action_type'] is None:
        details['action_type'] = BuildAction.COMPILE

    details['source'] = os.path.normpath(
        os.path.join(compilation_db_entry['directory'],
                     compilation_db_entry['file']))

    # In case the file attribute in the entry is empty.
    if details['source'] == '.':
        details['source'] = ''

    lang = get_language(os.path.splitext(details['source'])[1])
    if lang:
        if details['lang'] is None:
            details['lang'] = lang
    else:
        details['action_type'] = BuildAction.LINK

    # With gcc-toolchain a non default compiler toolchain can be set. Clang
    # will search for include paths and libraries based on the gcc-toolchain
    # parameter. Detecting extra include paths from the host compiler could
    # conflict with this.

    # For example if the compiler in the compile command is clang and
    # gcc-toolchain is set we will get the include paths for clang and not for
    # the compiler set in gcc-toolchain. This can cause missing headers during
    # the analysis.

    toolchain = \
        gcc_toolchain.toolchain_in_args(details['analyzer_options'])

    # Store the compiler built in include paths and defines.
    if not toolchain and 'ccache' not in details['compiler']:
        ImplicitCompilerInfo.set(details, compiler_info_file)

    return BuildAction(**details)


class CompileCommandEncoder(json.JSONEncoder):
    """JSON serializer for objects not serializable by default json code"""
    def default(self, o):
        if isinstance(o, BuildAction):
            return o.to_dict()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, o)


class CompileActionUniqueingType(object):
    NONE = 0  # Full Action text
    SOURCE_ALPHA = 1  # Based on source file, uniqueing by
    # on alphanumerically first target
    SOURCE_REGEX = 2  # Based on source file, uniqueing by regex filter
    STRICT = 3  # Gives error in case of duplicate


def parse_unique_log(compilation_database,
                     report_dir,
                     compile_uniqueing="none",
                     skip_handler=None,
                     compiler_info_file=None):
    """
    This function reads up the compilation_database
    and returns with a list of build actions that is prepared for clang
    execution. That means that gcc specific parameters are filtered out
    and gcc built in targets and include paths are added.
    It also filters out duplicate compilation actions based on the
    compile_uniqueing parameter.
    This function also dumps auto-detected the compiler info
    into <report_dir>/compiler_info.json.

    compilation_database -- A compilation database as a list of dict objects.
                            These object should contain "file", "dictionary"
                            and "command" keys. The "command" may be replaced
                            by "arguments" which is a split command. Older
                            versions of intercept-build provide the build
                            command this way.
    report_dir  -- The output report directory. The compiler infos
                   will be written to <report_dir>/compiler.info.json.
    compile_uniqueing -- Compilation database uniqueing mode.
                         If there are more than one compile commands for a
                         target file, only a single one is kept.
    skip_handler -- A SkipListHandler object which helps to skip build actions
                    that shouldn't be analyzed. The build actions described by
                    this handler will not be the part of the result list.
    compiler_info_file -- compiler_info.json. If exists, it will be used for
                    analysis.
    """
    try:
        uniqued_build_actions = dict()

        if compile_uniqueing == "alpha":
            build_action_uniqueing = CompileActionUniqueingType.SOURCE_ALPHA
        elif compile_uniqueing == "none":
            build_action_uniqueing = CompileActionUniqueingType.NONE
        elif compile_uniqueing == "strict":
            build_action_uniqueing = CompileActionUniqueingType.STRICT
        else:
            build_action_uniqueing = CompileActionUniqueingType.SOURCE_REGEX
            uniqueing_re = re.compile(compile_uniqueing)

        for entry in compilation_database:
            if skip_handler and skip_handler.should_skip(entry['file']):
                LOG.debug("SKIPPING FILE %s", entry['file'])
                continue
            action = parse_options(entry, compiler_info_file)

            if not action.lang:
                continue
            if action.action_type != BuildAction.COMPILE:
                continue
            if build_action_uniqueing == CompileActionUniqueingType.NONE:
                if action.__hash__ not in uniqued_build_actions:
                    uniqued_build_actions[action.__hash__] = action
            elif build_action_uniqueing == CompileActionUniqueingType.STRICT:
                if action.source not in uniqued_build_actions:
                    uniqued_build_actions[action.source] = action
                else:
                    LOG.error("Build Action uniqueing failed"
                              " as both '%s' and '%s'",
                              uniqued_build_actions[action.source]
                              .original_command,
                              action.original_command)
                    sys.exit(1)
            elif build_action_uniqueing ==\
                    CompileActionUniqueingType.SOURCE_ALPHA:
                if action.source not in uniqued_build_actions:
                    uniqued_build_actions[action.source] = action
                elif action.output <\
                        uniqued_build_actions[action.source].output:
                    uniqued_build_actions[action.source] = action
            elif build_action_uniqueing ==\
                    CompileActionUniqueingType.SOURCE_REGEX:
                LOG.debug("uniqueing regex")
                if action.source not in uniqued_build_actions:
                    uniqued_build_actions[action.source] = action
                elif uniqueing_re.match(action.original_command) and\
                    not uniqueing_re.match(
                        uniqued_build_actions[action.source].original_command):
                    uniqued_build_actions[action.source] = action
                elif uniqueing_re.match(action.original_command) and\
                    uniqueing_re.match(
                        uniqued_build_actions[action.source].original_command):
                    LOG.error("Build Action uniqueing failed as both \n %s"
                              "\n and \n %s \n match regex pattern:%s",
                              uniqued_build_actions[action.source].
                              original_command,
                              action.original_command,
                              compile_uniqueing)
                    sys.exit(1)

        compiler_info_out = os.path.join(report_dir, "compiler_info.json")
        with open(compiler_info_out, 'w') as f:
            LOG.debug("Writing compiler info into:"+compiler_info_out)
            json.dump(ImplicitCompilerInfo.get(), f)

        LOG.debug('Parsing log file done.')
        return list(uniqued_build_actions.values())

    except (ValueError, KeyError, TypeError) as ex:
        if not compilation_database:
            LOG.error('The compile database is empty.')
        else:
            LOG.error('The compile database is not valid.')
        LOG.debug(traceback.format_exc())
        LOG.debug(ex)
        sys.exit(1)
