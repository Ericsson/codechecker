# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Arranges the 1st phase of 2 phase executions for CTU
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import glob
import os
import shutil
import tempfile

from libcodechecker.analyze.analyzers import analyzer_base
from libcodechecker.analyze.analyzers import ctu_triple_arch
from libcodechecker.logger import get_logger

LOG = get_logger('analyzer')


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


def write_global_map(ctu_dir, arch, ctu_func_map_file, mangled_ast_pairs):
    """ Write (mangled function name, ast file) pairs into final file. """

    extern_fns_map_file = os.path.join(ctu_dir, arch, ctu_func_map_file)
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

    triple_arches = glob.glob(os.path.join(ctu_dir, '*'))
    for triple_path in triple_arches:
        if os.path.isdir(triple_path):
            triple_arch = os.path.basename(triple_path)
            fnmap_dir = os.path.join(ctu_dir, triple_arch,
                                     ctu_temp_fnmap_folder)

            func_map_lines = generate_func_map_lines(fnmap_dir)
            mangled_ast_pairs = create_global_ctu_function_map(func_map_lines)
            write_global_map(ctu_dir, triple_arch, ctu_func_map_file,
                             mangled_ast_pairs)

            # Remove all temporary files
            shutil.rmtree(fnmap_dir, ignore_errors=True)


def generate_ast(triple_arch, action, source, config, env):
    """ Generates ASTs for the current compilation command. """

    ast_joined_path = os.path.join(config.ctu_dir, triple_arch, 'ast',
                                   os.path.realpath(source)[1:] + '.ast')
    ast_path = os.path.abspath(ast_joined_path)
    ast_dir = os.path.dirname(ast_path)
    if not os.path.isdir(ast_dir):
        try:
            os.makedirs(ast_dir)
        except OSError:
            pass

    cmd = ctu_triple_arch.get_compile_command(action, config, source)
    # __clang__analyzer__ macro needs to be set in the imported TUs too.
    cmd.extend(['-emit-ast', '-D__clang_analyzer__', '-w', '-o', ast_path])

    cmdstr = ' '.join(cmd)
    LOG.debug_analyzer("Generating AST using '%s'", cmdstr)
    ret_code, _, err = analyzer_base.SourceAnalyzer.run_proc(cmdstr,
                                                             env,
                                                             action.directory)
    if ret_code != 0:
        LOG.error("Error generating AST.\n\ncommand:\n\n%s\n\nstderr:\n\n%s",
                  cmdstr, err)


def func_map_list_src_to_ast(func_src_list):
    """ Turns textual function map list with source files into a
    function map list with ast files. """

    func_ast_list = []
    for fn_src_txt in func_src_list:
        dpos = fn_src_txt.find(" ")
        mangled_name = fn_src_txt[0:dpos]
        path = fn_src_txt[dpos + 1:]
        # Normalize path on windows as well
        path = os.path.splitdrive(path)[1]
        # Make relative path out of absolute
        path = path[1:] if path[0] == os.sep else path
        ast_path = os.path.join("ast", path + ".ast")
        func_ast_list.append(mangled_name + " " + ast_path)
    return func_ast_list


def map_functions(triple_arch, action, source, config, env,
                  func_map_cmd, temp_fnmap_folder):
    """ Generate function map file for the current source. """

    cmd = ctu_triple_arch.get_compile_command(action, config)
    cmd[0] = func_map_cmd
    cmd.insert(1, source)
    cmd.insert(2, '--')

    cmdstr = ' '.join(cmd)
    LOG.debug_analyzer("Generating function map using '%s'", cmdstr)
    ret_code, stdout, err \
        = analyzer_base.SourceAnalyzer.run_proc(cmdstr,
                                                env,
                                                action.directory)
    if ret_code != 0:
        LOG.error("Error generating function map."
                  "\n\ncommand:\n\n%s\n\nstderr:\n\n%s", cmdstr, err)
        return

    func_src_list = stdout.splitlines()
    func_ast_list = func_map_list_src_to_ast(func_src_list)
    extern_fns_map_folder = os.path.join(config.ctu_dir, triple_arch,
                                         temp_fnmap_folder)
    if not os.path.isdir(extern_fns_map_folder):
        try:
            os.makedirs(extern_fns_map_folder)
        except OSError:
            pass

    if func_ast_list:
        with tempfile.NamedTemporaryFile(mode='w',
                                         dir=extern_fns_map_folder,
                                         delete=False) as out_file:
            out_file.write("\n".join(func_ast_list) + "\n")
