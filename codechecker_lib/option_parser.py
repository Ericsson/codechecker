# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import re
import shlex

from codechecker_lib import logger

LOG = logger.get_new_logger('OPTION PARSER')

# TODO: make modular option handling system,
# configuring possibility from config file
# class OpenFilterPluginBase(object):
#     __metaclass__ = abc.ABCMeta
#
#     @abc.abstractproperty
#     def compiler_name(self):
#         ''' Compiler name (regex expression)'''
#         return None
#
#     @abc.abstactmethod
#     def get_exclude_rules(self):
#         ''' Remove options, x -> nothing'''
#         return {}
#
#     @abc.abstactmethod
#     def get_modify_rules(self):
#         ''' Modify options, x -> y'''
#         return {}
#
#     @abc.abstactmethod
#     def get_add_rules(self):
#         ''' Add rules,::x '''
#         return []
#
# class DefaultFilterPlugin(OpenFilterPluginBase):
#     __compiler_name = '.*'
#
#     @property
#     def compiler_name(self):
#         return __compiler_name
#
#     def get_exclude_rules(self):
#         return {}
#
#     def get_modify_rules(self):
#         return {}
#
#     def get_add_rules(self):
#         return []

# ---------------------------------------------------------------------------- #
#  Lookup tables. From ScanBuild: clang-analyzer.llvm.org/scan-build.html
# ---------------------------------------------------------------------------- #

COMPILE_OPTION_MAP = {
    '-nostdinc': 0,
    '-include': 1,
    '-idirafter': 1,
    '-imacros': 1,
    '-iprefix': 1,
    '-isystem': 1,
    '-iwithprefix': 1,
    '-iwithprefixbefore': 1
}

COMPILE_OPTION_MAP_REGEX = {
    '-O([1-3]|s)?$': 0,
    '-std=.*': 0,
    '^-f.*': 0,
    '-m.*': 0,
    '^-Wno-.*': 0,
    '^-m(32|64)$': 0
}

COMPILE_OPTION_MAP_MERGED = [
    '^-iquote(.*)$',
    '^-[DIU](.*)$',
    '^-F(.+)$'
]

COMPILER_LINKER_OPTION_MAP = {
    '-write-strings': 0,
    '-ftrapv-handler': 1,
    '-mios-simulator-version-min': 0,
    '-sysroot': 1,
    '-stdlib': 0,
    '-target': 1,
    '-v': 0,
    '-mmacosx-version-min': 0,
    '-miphoneos-version-min': 0
}

LINKER_OPTION_MAP = {
    '-framework': 1,
    '-fobjc-link-runtime': 0
}

IGNORED_OPTION_MAP = {
    '-MT': 1,
    '-MF': 1,
    '-fsyntax-only': 0,
    '-save-temps': 0,
    '-install_name': 1,
    '-exported_symbols_list': 1,
    '-current_version': 1,
    '-compatibility_version': 1,
    '-init': 1,
    '-e': 1,
    '-seg1addr': 1,
    '-bundle_loader': 1,
    '-multiply_defined': 1,
    '-sectorder': 3,
    '--param': 1,
    '-u': 1,
    '--serialize-diagnostics': 1
}

UNIQUE_OPTIONS = {
    '-isysroot': 1
}

REPLACE_OPTIONS_MAP = {
    '-mips32'       : [ '-target', 'mips', '-mips32' ],
    '-mips64'       : [ '-target', 'mips64', '-mips64' ],
    '-mpowerpc'     : [ '-target', 'powerpc' ],
    '-mpowerpc64'   : [ '-target', 'powerpc64' ]
}

UNKNOWN_OPTIONS_MAP_REGEX = {
    '^-mmultiple$': 0,
    '^-mupdate$': 0,
    '^-m(no-)?string$': 0,
    '^-m(no-)?sdata.*$': 0,
    '^-mfix-cortex-m3-ldrd$': 0,
    '^-mthumb-interwork$': 0
}

# -----------------------------------------------------------------------------
class ActionType(object):
    LINK, COMPILE, PREPROCESS, INFO = range(4)


# -----------------------------------------------------------------------------
class OptionParserResult(object):

    def __init__(self):
        self._action = ActionType.LINK
        self._compile_opts = []
        self._link_opts = []
        self._files = []
        self._arch = ''
        self._lang = None
        self._output = ''

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, value):
        self._action = value

    @property
    def compile_opts(self):
        return self._compile_opts

    @compile_opts.setter
    def compile_opts(self, value):
        self._compile_opts = value

    @property
    def link_opts(self):
        return self._link_opts

    @link_opts.setter
    def link_opts(self, value):
        self._link_opts = value

    @property
    def files(self):
        return self._files

    @files.setter
    def files(self, value):
        self._files = value

    @property
    def arch(self):
        return self._arch

    @arch.setter
    def arch(self, value):
        self._arch = value

    @property
    def lang(self):
        return self._lang

    @lang.setter
    def lang(self, value):
        self._lang = value

    @property
    def output(self):
        return self._output

    @output.setter
    def output(self, value):
        self._output = value


# -----------------------------------------------------------------------------
class OptionIterator(object):

    def __init__(self, args):
        self._item = None
        self._it = iter(args)

    def next(self):
        self._item = next(self._it)
        return self  # ._item

    def __iter__(self):
        return self

    @property
    def item(self):
        return self._item


# -----------------------------------------------------------------------------
def arg_check(it, result):
    def regex_match(string, pattern):
        regexp = re.compile(pattern)
        match = regexp.match(string)
        return match is not None

    # Handler functions for options
    def append_to_list(table, target_list, regex=False):
        '''Append n item from iterator to to result[att_name] list.'''
        def wrapped(value):
            def append_n(size):
                target_list.append(it.item)
                for x in xrange(0, size):
                    it.next()
                    target_list.append(it.item)

            if regex:
                for pattern in table:
                    if regex_match(value, pattern):
                        append_n(table[pattern])
                        return True
            elif value in table:
                append_n(table[value])
                return True
            return False
        return wrapped

    def append_merged_to_list(table, target_list):
        ''' Append one or two item to the list.
                1: if there is no space between two option.
                2: otherwise.
        '''
        def wrapped(value):
            for pattern in table:
                match = re.match(pattern, value)
                if match is not None:
                    tmp = it.item
                    if match.group(1) == '':
                        it.next()
                        tmp = tmp + it.item
                    target_list.append(tmp)
                    return True
            return False
        return wrapped

    def append_to_list_from_file(arg, target_list):
        '''Append items from file to to result[att_name] list.'''
        def wrapped(value):
            if value == arg:
                it.next()
                with open(it.item) as file:
                    for line in file:
                        target_list.append(line.strip())
                return True
            return False
        return wrapped

    def append_replacement_to_list(table, target_list, regex=False):
        '''Append replacement items from table to to result[att_name] list.'''
        def wrapped(value):
            def append_replacement(items):
                for item in items:
                    target_list.append(item)
                it.next()

            if regex:
                for pattern in table:
                    if regex_match(value, pattern):
                        append_replacement(table[pattern])
                        return True
            elif value in table:
                append_replacement(table[value])
                return True
            return False
        return wrapped

    def set_attr(arg, attr_name, attr_value=None, regex=None):
        '''Set an attr value. If no value given then read next from iterator.'''
        def wrapped(value):
            if (regex and regex_match(value, arg)) or value == arg:
                tmp = attr_value
                if attr_value is None:
                    it.next()
                    tmp = it.item
                attr_name = tmp
                return True
            return False
        return wrapped

    def skip(table, regex=False):
        '''Skip n item in iterator.'''
        def wrapped(value):
            def skip_n(size):
                for x in xrange(0, size):
                    it.next()

            if regex:
                for pattern in table:
                    if regex_match(value, pattern):
                        table[pattern]
                        return True
            elif value in table:
                skip_n(table[value])
                return True
            return False
        return wrapped

    # Defines handler functions for tables and single options
    arg_collection = [
        append_replacement_to_list(REPLACE_OPTIONS_MAP, result.compile_opts),
        skip(UNKNOWN_OPTIONS_MAP_REGEX, True),
        append_to_list(COMPILE_OPTION_MAP, result.compile_opts),
        append_to_list(COMPILER_LINKER_OPTION_MAP, result.compile_opts),
        append_to_list(COMPILE_OPTION_MAP_REGEX, result.compile_opts, True),
        append_merged_to_list(COMPILE_OPTION_MAP_MERGED, result.compile_opts),
        set_attr('-x', result.lang),
        set_attr('-o', result.output),
        set_attr('-arch', result.arch),
        set_attr('-c', result.action, ActionType.COMPILE),
        set_attr('^-(E|MM?)$', result.action, ActionType.PREPROCESS, True),
        set_attr('-print-prog-name', result.action, ActionType.INFO),
        skip(LINKER_OPTION_MAP),
        skip(IGNORED_OPTION_MAP),
        skip(UNIQUE_OPTIONS),
        append_to_list_from_file('-filelist', result.files),
        append_to_list({'^[^-].+': 0}, result.files, True)]

    return any((collection(it.item) for collection in arg_collection))


# -----------------------------------------------------------------------------
def parse_options(args):
    '''Requires a full compile command with the compiler, not only arguments.'''

    result_map = OptionParserResult()
    for it in OptionIterator(shlex.split(args)[1:]):
        arg_check(it, result_map)  # TODO: do sth at False result, actually skip

    return result_map


# -----------------------------------------------------------------------------
def get_language(extension):
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
    lang = mapping.get(extension) if extension in mapping else None
    return lang
