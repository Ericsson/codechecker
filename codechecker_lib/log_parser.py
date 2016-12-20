# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import traceback
import subprocess
import shlex


from codechecker_lib import build_action
from codechecker_lib import option_parser
from codechecker_lib.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('LOG PARSER')


# -----------------------------------------------------------------------------
def get_compiler_includes(compiler):
    """
    Returns a list of default includes of the given compiler.
    """
    LOG.debug_analyzer('getting include paths for  ' + compiler)
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

        print_line = False
        for line in err.splitlines(True):
            if line.startswith(end_mark):
                print_line = False
            if print_line:
                include_paths.append("-I"+line.strip())
            if line.startswith(start_mark):
                print_line = True

    except OSError as oerr:
        LOG.error("Cannot find include paths:" + oerr.strerror+"\n")

    finally:
        return include_paths


# -----------------------------------------------------------------------------
def get_compiler_defines(compiler):
    """
    Returns a list of default defines of the given compiler.
    """
    cmd = compiler + " -dM -E -"
    defines = []
    FNULL = open(os.devnull, 'r')
    try:
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
    LOG.debug_analyzer('parse_compile_commands_json: ' +
                       str(add_compiler_defaults))

    actions = []
    filtered_build_actions = {}

    logfile.seek(0)
    data = json.load(logfile)

    compiler_defines = {}
    compiler_includes = {}

    counter = 0
    for entry in data:
        sourcefile = entry['file']
        lang = option_parser.get_language(sourcefile[sourcefile.rfind('.'):])

        if not lang:
            continue

        action = build_action.BuildAction(counter)

        command = entry['command']
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
    LOG.debug_analyzer('Parsing log file: ' + logfilepath)
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

    LOG.debug_analyzer('Parsing log file done.')
    return actions
