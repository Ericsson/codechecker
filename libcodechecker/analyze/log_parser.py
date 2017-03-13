# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import sys
import traceback
import subprocess
import shlex

# TODO: This is a cross-subpackage import!
from libcodechecker.log import build_action
from libcodechecker.log import option_parser
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('LOG PARSER')


# -----------------------------------------------------------------------------
def get_compiler_includes(compiler):
    """
    Returns a list of default includes of the given compiler.
    """
    LOG.debug('getting include paths for  ' + compiler)
    start_mark = "#include <...> search starts here:"
    end_mark = "End of search list."

    cmd = compiler + " -E -x c++ - -v "  # what if not c++?
    include_paths = []
    try:
        proc = subprocess.Popen(shlex.split(cmd),
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        out, err = proc.communicate("")

        do_append = False
        for line in err.splitlines(True):
            line = line.strip()
            if line.startswith(end_mark):
                do_append = False
            if do_append:
                include_paths.append("-I"+line)
            if line.startswith(start_mark):
                do_append = True

    except OSError as oerr:
        LOG.error("Cannot find include paths:" + oerr.strerror+"\n")
    return include_paths


# -----------------------------------------------------------------------------
def get_compiler_defines(compiler):
    """
    Returns a list of default defines of the given compiler.
    """
    cmd = compiler + " -dM -E -"
    defines = []
    try:
        with open(os.devnull, 'r') as FNULL:
            proc = subprocess.Popen(shlex.split(cmd),
                                    stdin=FNULL,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            out, err = proc.communicate("")
            for line in out.splitlines(True):
                LOG.debug("define:"+line)
                define = line.strip().split(" ")[1:]
                d = "-D"+define[0] + '=' + '"' + ' '.join(define[1:]) + '"'
                defines.append(d)
    except OSError as oerr:
        LOG.error("Cannot find defines:" + oerr.strerror+"\n")
    return defines


# -----------------------------------------------------------------------------
def parse_compile_commands_json(logfile, add_compiler_defaults=False):
    import json
    LOG.debug('parse_compile_commands_json: ' + str(add_compiler_defaults))

    actions = []
    filtered_build_actions = {}

    logfile.seek(0)
    data = json.load(logfile)

    compiler_defines = {}
    compiler_includes = {}

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
        elif 'arguments' in entry:
            # Newest versions of intercept-build create an argument vector
            # instead of a command string.
            for i in range(0, len(entry['arguments'])):
                arg = entry['arguments'][i]
                if ' ' in arg:
                    # If there is an argument with a space in it, the join
                    # below will mess the invocation up. (-DVAR=va lue will be
                    # passed as -DVAR=va)
                    #
                    # Build.json created by ld-logger escapes these strings
                    # and they never reach the analyser later on.
                    #
                    # TODO: Better handle this. (See issue #505.)
                    entry['arguments'][i] = '\"' + arg + '\"'
            command = ' '.join(entry['arguments'])
        else:
            raise KeyError("No valid 'command' or 'arguments' entry found!")
        results = option_parser.parse_options(command)

        action.original_command = command
        action.analyzer_options = results.compile_opts
        action.lang = results.lang
        action.target = results.arch

        # store the compiler built in include paths
        # and defines
        if add_compiler_defaults and results.compiler:
            if not (results.compiler in compiler_defines):
                compiler_defines[results.compiler] = \
                    get_compiler_defines(results.compiler)
                compiler_includes[results.compiler] = \
                    get_compiler_includes(results.compiler)
            action.compiler_defines = compiler_defines[results.compiler]
            action.compiler_includes = compiler_includes[results.compiler]

        if results.action == option_parser.ActionType.COMPILE or \
           results.action == option_parser.ActionType.LINK:
            action.skip = False

        # TODO: check arch.
        action.directory = entry['directory']
        action.sources = sourcefile
        # Filter out duplicate compilation commands.
        unique_key = action.cmp_key
        if filtered_build_actions.get(unique_key) is None:
            filtered_build_actions[unique_key] = action

        del action
        counter += 1

    for ba_hash, ba in filtered_build_actions.items():
        actions.append(ba)

    return actions


# -----------------------------------------------------------------------------
def parse_log(logfilepath, add_compiler_defaults=False):
    LOG.debug('Parsing log file: ' + logfilepath)
    actions = []

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
