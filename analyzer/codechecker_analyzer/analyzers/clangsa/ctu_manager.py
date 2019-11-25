# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Arranges the 1st phase of 2 phase executions for CTU
"""


import glob
import os
import shutil
import tempfile

from codechecker_common.logger import get_logger

from merge_clang_extdef_mappings.merge import merge

from .. import analyzer_base
from . import ctu_triple_arch

LOG = get_logger('analyzer')


def merge_clang_extdef_mappings(ctu_dir, ctu_func_map_file,
                                ctu_temp_fnmap_folder):
    """ Merge individual function maps into a global one."""

    triple_arches = glob.glob(os.path.join(ctu_dir, '*'))
    for triple_path in triple_arches:
        if not os.path.isdir(triple_path):
            continue

        triple_arch = os.path.basename(triple_path)
        fnmap_dir = os.path.join(ctu_dir, triple_arch,
                                 ctu_temp_fnmap_folder)

        merged_fn_map = os.path.join(ctu_dir, triple_arch,
                                     ctu_func_map_file)
        merge(fnmap_dir, merged_fn_map)

        # Remove all temporary files.
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
    ret_code, _, err = analyzer_base.SourceAnalyzer.run_proc(cmd,
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
        = analyzer_base.SourceAnalyzer.run_proc(cmd,
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
                                         delete=False,
                                         encoding='utf-8') as out_file:
            out_file.write("\n".join(func_ast_list) + "\n")
