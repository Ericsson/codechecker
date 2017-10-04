# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import re
import sys
import traceback
import subprocess
import shlex

# TODO: This is a cross-subpackage import!
from libcodechecker.log import build_action
from libcodechecker.log import option_parser
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('LOG PARSER')


# If these options are present in the original build command, they must
# be forwarded to get_compiler_includes and get_compiler_defines so the
# resulting includes point to the target that was used in the build.
COMPILE_OPTS_FWD_TO_DEFAULTS_GETTER = frozenset(
    ['^-m(32|64)',
     '^-std=.*'])


def get_compiler_includes(compiler, lang, compile_opts, extra_opts=None):
    """
    Returns a list of default includes of the given compiler.
    """
    start_mark = "#include <...> search starts here:"
    end_mark = "End of search list."

    if extra_opts is None:
        extra_opts = []

    # The first sysroot flag found among the compilation options is added
    # to the command below to give a more precise default include list.
    # Absence of any sysroot flags results in an empty string.
    sysroot = next(
        (item for item in compile_opts if item.startswith("--sysroot=")), "")

    cmd = compiler + " " + ' '.join(extra_opts) + " -E -x " + lang + \
        " " + sysroot + " - -v "

    LOG.debug("Retrieving default includes via '" + cmd + "'")
    include_paths = []
    try:
        proc = subprocess.Popen(shlex.split(cmd),
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        _, err = proc.communicate("")

        do_append = False
        for line in err.splitlines(True):
            line = line.strip()
            if line.startswith(end_mark):
                do_append = False
            if do_append:
                # On OSX there are framework includes,
                # where we need to strip the "(framework directory)" string.
                # For instance:
                # /System/Library/Frameworks (framework directory)
                fpos = line.find("(framework directory)")
                if fpos == -1:
                    include_paths.append("-isystem " + line)
                else:
                    include_paths.append("-isystem " + line[0:fpos-1])

            if line.startswith(start_mark):
                do_append = True

    except OSError as oerr:
        LOG.error("Cannot find include paths: " + oerr.strerror + "\n")
    return include_paths


def get_compiler_target(compiler):
    """
    Returns the target triple of the given compiler as a string.

    """
    target_label = "Target:"
    target = ""

    cmd = compiler + ' -v'
    LOG.debug("Retrieving target platform information via '" + cmd + "'")

    try:
        proc = subprocess.Popen(shlex.split(cmd),
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        _, err = proc.communicate("")
        for line in err.splitlines(True):
            line = line.strip().split()
            if line[0] == target_label:
                target = line[1]

    except OSError as oerr:
        LOG.error("Cannot find compiler target: " + oerr.strerror + "\n")

    return target


def parse_compile_commands_json(logfile, add_compiler_defaults=False):
    import json
    # The add-compiler-defaults is a deprecated argument
    # and we always perform target and include auto-detection.
    add_compiler_defaults = True
    LOG.debug('parse_compile_commands_json: ' + str(add_compiler_defaults))

    actions = []
    filtered_build_actions = {}

    logfile.seek(0)
    data = json.load(logfile)

    compiler_includes = {}
    compiler_target = ''

    counter = 0
    for entry in data:
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
        action.analyzer_options = results.compile_opts

        action.lang = results.lang
        action.target = results.arch

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
                    get_compiler_includes(results.compiler, results.lang,
                                          results.compile_opts, extra_opts)
                compiler_target = get_compiler_target(results.compiler)
            action.compiler_includes = compiler_includes[results.compiler]

            if compiler_target != "":
                action.analyzer_options.append("--target=" + compiler_target)

        if results.action == option_parser.ActionType.COMPILE or \
           results.action == option_parser.ActionType.LINK:
            action.skip = False

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


def parse_log(logfilepath, add_compiler_defaults=False):
    LOG.debug('Parsing log file: ' + logfilepath)

    with open(logfilepath) as logfile:
        try:
            actions = \
                parse_compile_commands_json(logfile, add_compiler_defaults)
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
