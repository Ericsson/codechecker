# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Arranges the 1st phase of 2 phase executions for CTU
"""

import glob
import multiprocessing
import os
import shlex
import shutil
import signal
import sys
import tempfile
import traceback

from libcodechecker.analyze.analyzers import analyzer_base
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.analyze import analyzer_env
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('CTU MANAGER')


def generate_func_map_lines(fnmap_dir):
    """ Iterate over all lines of input files in random order. """

    files = glob.glob(os.path.join(fnmap_dir, '*'))
    for filename in files:
        with open(filename, 'r') as in_file:
            for line in in_file:
                yield line


def create_global_ctu_function_map(func_map_lines):
    """ Takes iterator of individual function maps and creates a global map
    keeping only unique names. We leave conflicting names out of CTU.
    A function map contains the id of a function (mangled name) and the
    originating source (the corresponding AST file) name."""

    mangled_to_asts = {}

    for line in func_map_lines:
        mangled_name, ast_file = line.strip().split(' ', 1)
        # We collect all occurences of a function name into a list
        if mangled_name not in mangled_to_asts:
            mangled_to_asts[mangled_name] = {ast_file}
        else:
            mangled_to_asts[mangled_name].add(ast_file)

    mangled_ast_pairs = []

    for mangled_name, ast_files in mangled_to_asts.items():
        if len(ast_files) == 1:
            mangled_ast_pairs.append((mangled_name, ast_files.pop()))

    return mangled_ast_pairs


def write_global_map(ctu_dir, ctu_func_map_file, mangled_ast_pairs):
    """ Write (mangled function name, ast file) pairs into final file. """

    extern_fns_map_file = os.path.join(ctu_dir, ctu_func_map_file)
    with open(extern_fns_map_file, 'w') as out_file:
        for mangled_name, ast_file in mangled_ast_pairs:
            out_file.write('%s %s\n' % (mangled_name, ast_file))


def merge_ctu_func_maps(ctu_dir, ctu_func_map_file, ctu_temp_fnmap_folder):
    """ Merge individual function maps into a global one.

    As the collect phase runs parallel on multiple threads, all compilation
    units are separately mapped into a temporary file in ctu_temp_fnmap_folder.
    These function maps contain the mangled names of functions and the source
    (AST generated from the source) which had them.
    These files should be merged at the end into a global map file:
    ctu_func_map_file."""

    fnmap_dir = os.path.join(ctu_dir, ctu_temp_fnmap_folder)

    func_map_lines = generate_func_map_lines(fnmap_dir)
    mangled_ast_pairs = create_global_ctu_function_map(func_map_lines)
    write_global_map(ctu_dir, ctu_func_map_file, mangled_ast_pairs)

    # Remove all temporary files
    shutil.rmtree(fnmap_dir, ignore_errors=True)


def get_compile_command(action, config, source='', output=''):
    """ Generate a standardized and cleaned compile command serving as a base
    for other operations. """

    cmd = [config.analyzer_binary]
    cmd.extend(action.compiler_defines)
    cmd.extend(action.compiler_includes)
    if len(config.compiler_resource_dir) > 0:
        cmd.extend(['-resource-dir', config.compiler_resource_dir,
                    '-isystem', config.compiler_resource_dir])
    cmd.append('-c')
    if config.compiler_sysroot:
        cmd.extend(['--sysroot', config.compiler_sysroot])
    for path in config.system_includes:
        cmd.extend(['-isystem', path])
    for path in config.includes:
        cmd.extend(['-I', path])
    cmd.extend(['-x', action.lang])
    cmd.append(config.analyzer_extra_arguments)
    cmd.extend(action.analyzer_options)
    if output:
        cmd.extend(['-o', output])
    if source:
        cmd.append(source)
    return cmd


def get_triple_arch(action, source, config, env):
    """Returns the architecture part of the target triple for the given
    compilation command. """

    cmd = get_compile_command(action, config, source)
    cmd.insert(1, '-###')
    cmdstr = ' '.join(cmd)
    _, stdout, stderr = analyzer_base.SourceAnalyzer.run_proc(cmdstr, env)
    last_line = (stdout + stderr).splitlines()[-1]
    res_cmd = shlex.split(last_line)
    arch = ""
    i = 0
    while i < len(res_cmd) and res_cmd[i] != "-triple":
        i += 1
    if i < (len(res_cmd) - 1):
        arch = res_cmd[i + 1].split("-")[0]
    return arch


def generate_ast(triple_arch, action, source, config, env):
    """ Generates ASTs for the current compilation command. """

    ast_joined_path = os.path.join(config.ctu_dir, 'ast', triple_arch,
                                   os.path.realpath(source)[1:] + '.ast')
    ast_path = os.path.abspath(ast_joined_path)
    ast_dir = os.path.dirname(ast_path)
    if not os.path.isdir(ast_dir):
        os.makedirs(ast_dir)

    cmd = get_compile_command(action, config, source)
    cmd.extend(['-emit-ast', '-w', '-o', ast_path])

    cmdstr = ' '.join(cmd)
    LOG.debug_analyzer("Generating AST using '%s'" % cmdstr)
    ret_code, _, _ = analyzer_base.SourceAnalyzer.run_proc(cmdstr, env)
    if ret_code != 0:
        LOG.error("Error generating AST using '%s'", cmdstr)


def func_map_list_src_to_ast(func_src_list, triple_arch, ctu_in_memory):
    """ Turns textual function map list with source files into a
    function map list with ast files. """

    func_ast_list = []
    for fn_src_txt in func_src_list:
        dpos = fn_src_txt.find(" ")
        mangled_name = fn_src_txt[0:dpos]
        path = fn_src_txt[dpos + 1:]
        if ctu_in_memory:
            ast_path = path
        else:
            # Normalize path on windows as well
            path = os.path.splitdrive(path)[1]
            # Make relative path out of absolute
            path = path[1:] if path[0] == os.sep else path
            ast_path = os.path.join("ast", triple_arch, path + ".ast")
        func_ast_list.append(mangled_name + "@" + triple_arch + " " + ast_path)
    return func_ast_list


def map_functions(triple_arch, action, source, config, env,
                  func_map_cmd, temp_fnmap_folder):
    """ Generate function map file for the current source. """

    cmd = get_compile_command(action, config)
    cmd[0] = func_map_cmd
    cmd.insert(1, source)
    cmd.insert(2, '--')

    cmdstr = ' '.join(cmd)
    LOG.debug_analyzer("Generating function map using '%s'" % cmdstr)
    ret_code, stdout, _ = analyzer_base.SourceAnalyzer.run_proc(cmdstr, env)
    if ret_code != 0:
        LOG.error("Error generating function map using '%s'", cmdstr)
        return

    func_src_list = stdout.splitlines()
    func_ast_list = func_map_list_src_to_ast(func_src_list, triple_arch,
                                             config.ctu_in_memory)
    extern_fns_map_folder = os.path.join(config.ctu_dir, temp_fnmap_folder)
    if func_ast_list:
        with tempfile.NamedTemporaryFile(mode='w',
                                         dir=extern_fns_map_folder,
                                         delete=False) as out_file:
            out_file.write("\n".join(func_ast_list) + "\n")


def collect_build_action(params):
    """ Preprocess sources by generating all data needed by CTU analysis. """

    action, context, analyzer_config_map, skip_handler, \
        ctu_temp_fnmap_folder = params

    try:
        for source in action.sources:
            if skip_handler and skip_handler.should_skip(source):
                continue
            if action.analyzer_type != analyzer_types.CLANG_SA:
                continue
            config = analyzer_config_map.get(analyzer_types.CLANG_SA)
            analyzer_environment = analyzer_env.get_check_env(
                context.path_env_extra,
                context.ld_lib_path_extra)
            triple_arch = get_triple_arch(action, source, config,
                                          analyzer_environment)
            if not config.ctu_in_memory:
                generate_ast(triple_arch, action, source, config,
                             analyzer_environment)
            map_functions(triple_arch, action, source, config,
                          analyzer_environment, context.ctu_func_map_cmd,
                          ctu_temp_fnmap_folder)
    except Exception as ex:
        LOG.debug_analyzer(str(ex))
        traceback.print_exc(file=sys.stdout)
        raise


def do_ctu_collect(actions, context, analyzer_config_map,
                   jobs, skip_handler, ctu_dir):
    """
    Start the workers for CTU collect phase.
    """

    def signal_handler(*arg, **kwarg):
        try:
            pool.terminate()
        finally:
            sys.exit(1)

    ctu_temp_fnmap_folder = 'tmpExternalFnMaps'
    ctu_func_map_file = 'externalFnMap.txt'

    os.makedirs(os.path.join(ctu_dir, ctu_temp_fnmap_folder))
    signal.signal(signal.SIGINT, signal_handler)
    pool = multiprocessing.Pool(jobs)
    try:
        collect_actions = [(build_action,
                            context,
                            analyzer_config_map,
                            skip_handler,
                            ctu_temp_fnmap_folder)
                           for build_action in actions]
        pool.map_async(collect_build_action, collect_actions).get(float('inf'))
        pool.close()
    except Exception:
        pool.terminate()
        raise
    finally:
        pool.join()

    merge_ctu_func_maps(ctu_dir,
                        ctu_func_map_file,
                        ctu_temp_fnmap_folder)
