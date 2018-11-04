# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import re
import shlex

from build_action import BuildAction

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
    '-MM',
    '-MP',
    '-MD',
    '-MV',
    '-MMD',
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
    '-MT': 1,
    '-MQ': 1,
    '-MF': 1,
    '-MJ': 1,
    '-install_name': 1,
    '-exported_symbols_list': 1,
    '-current_version': 1,
    '-compatibility_version': 1,
    '-init$': 1,
    '-e$': 1,
    '-seg1addr': 1,
    '-bundle_loader': 1,
    '-multiply_defined': 1,
    '-sectorder': 3,
    '--param$': 1,
    '-u$': 1,
    '--serialize-diagnostics': 1,
    '-framework': 1,
    # Skip paired Xclang options like "-Xclang -mllvm".
    '-Xclang': 1
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


def __append_from_file(flag_iterator, target, buildaction):
    if flag_iterator.item == '-filelist':
        next(flag_iterator)

        with open(flag_iterator.item) as f:
            for line in f:
                # TODO: What kind of flags are these? Shouldn't these be
                # appended to the compilation options collected in the
                # buildaction object?
                target.append(line.strip())

        return True

    return False


def __collect_compile_opts(flag_iterator, target, buildaction):
    """
    This function collects the compilation (i.e. not linker or preprocessor)
    flags to the buildaction and saves to the target command.
    """
    if COMPILE_OPTIONS.match(flag_iterator.item):
        target.append(flag_iterator.item)
        buildaction.analyzer_options.append(flag_iterator.item)
        return True

    m = COMPILE_OPTIONS_MERGED.match(flag_iterator.item)

    if m:
        target.append(flag_iterator.item)
        buildaction.analyzer_options.append(flag_iterator.item)

        if len(m.group(0)) == len(flag_iterator.item):
            next(flag_iterator)
            target.append(flag_iterator.item)
            buildaction.analyzer_options.append(flag_iterator.item)

        return True

    return False


def __collect_sources(flag_iterator, target, buildaction):
    """
    This function collects the compiled source file names (i.e. the arguments
    which don't start with a dash character) to the buildaction object and
    appends it to the target command.
    """
    if flag_iterator.item[0] != '-':
        target.append(flag_iterator.item)
        buildaction.sources = flag_iterator.item.strip('"')
        return True

    return False


def __determine_action_type(flag_iterator, target, buildaction):
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
    elif re.match('-(E|M[T|Q|F|J|P|V|M]*)$', flag_iterator.item):
        buildaction.action_type = BuildAction.PREPROCESS
        return True

    return False


def __get_arch(flag_iterator, target, buildaction):
    """
    This function consumes -arch flag which is followed by the target
    architecture. This is then collected to the buildaction object and saved to
    the target command.
    """
    # TODO: Is this really a target architecture? Have we seen this flag being
    # used in a real project? This -arch flag is not really documented among
    # GCC flags.
    # Where do we use this architecture during analysis and why?
    if flag_iterator.item == '-arch':
        target.append('-arch')
        next(flag_iterator)
        target.append(flag_iterator.item)
        buildaction.target = flag_iterator.item
        return True

    return False


def __get_language(flag_iterator, target, buildaction):
    """
    This function consumes -x flag which is followed by the language. This
    language is then collected to the buildaction object and saved to the
    target command.
    """
    # TODO: Known issue: a -x flag may precede all source files in the build
    # command with different languages.
    if flag_iterator.item == '-x':
        target.append('-x')
        next(flag_iterator)
        target.append(flag_iterator.item)
        buildaction.lang = flag_iterator.item
        return True

    return False


def __get_output(flag_iterator, target, buildaction):
    """
    This function consumes -o flag which is followed by the output file of the
    action. This file is then collected to the buildaction object and saved to
    the target command.
    """
    if flag_iterator.item == '-o':
        target.append('-o')
        next(flag_iterator)
        target.append(flag_iterator.item)
        buildaction.output = flag_iterator.item
        return True

    return False


def __replace(flag_iterator, target, buildaction):
    """
    This function extends the target list with the corresponding replacement
    based on REPLACE_OPTIONS_MAP if the flag_iterator is currently pointing to
    a flag to replace.
    """
    value = REPLACE_OPTIONS_MAP.get(flag_iterator.item)

    if value:
        target.extend(value)

    return bool(value)


def __skip(flag_iterator, target, buildaction):
    """
    This function skips the flag pointed by the given flag_iterator with its
    parameters if any.
    """
    if IGNORED_OPTIONS.match(flag_iterator.item):
        return True

    for pattern, arg_num in IGNORED_PARAM_OPTIONS.items():
        if re.match(pattern, flag_iterator.item):
            for i in range(arg_num):
                next(flag_iterator)
            return True

    return False


def parse_options(gcc_command):
    """
    This function parses a GCC compilation action and returns a BuildAction
    object which can be the input of Clang analyzer tools.

    gcc_command -- A valid GCC build command.
    """

    buildaction = BuildAction()

    # Keep " characters.
    gcc_command = gcc_command.replace(r'"', r'"\"')
    gcc_command = shlex.split(gcc_command)

    buildaction.action_type = buildaction.COMPILE
    buildaction.compiler = gcc_command[0]
    if '++' in buildaction.compiler or 'cpp' in buildaction.compiler:
        buildaction.lang = 'c++'

    clang_command = [gcc_command[0]]

    flag_transformers = [
        __get_arch,
        __get_language,
        __get_output,
        __determine_action_type,
        __replace,
        __skip,
        __append_from_file,
        __collect_compile_opts]

    for it in OptionIterator(gcc_command[1:]):
        for flag_transformer in flag_transformers:
            if flag_transformer(it, clang_command, buildaction):
                break
        else:
            clang_command.append(it.item)
            #print('Unhandled argument: ' + it.item)

    # TODO: It is difficult to fetch source files from a compilation command if
    # they contain a space character.
    #for source_file in buildaction.sources:
    #    lang = get_language(os.path.splitext(source_file)[1])
    #    if lang:
    #        if buildaction.lang is None:
    #            buildaction.lang = lang
    #        break
    #else:
    #    buildaction.action_type = BuildAction.LINK

    return buildaction
