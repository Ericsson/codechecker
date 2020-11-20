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
import yaml
import os
import shutil
import tempfile
from pathlib import Path
from sys import maxsize

from codechecker_common.logger import get_logger

from codechecker_merge_clang_extdef_mappings.merge_clang_extdef_mappings \
    import merge

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


def generate_ast_cmd(action, config, triple_arch, source):
    """ Command to generate AST (or PCH) file. """
    ast_joined_path = os.path.join(config.ctu_dir, triple_arch, 'ast',
                                   os.path.realpath(source)[1:] + '.ast')
    ast_path = os.path.abspath(ast_joined_path)
    ast_dir = os.path.dirname(ast_path)

    cmd = ctu_triple_arch.get_compile_command(action, config, source)

    # __clang__analyzer__ macro needs to be set in the imported TUs too.
    cmd.extend(['-emit-ast', '-D__clang_analyzer__', '-w', '-o', ast_path])

    return cmd, ast_dir


def generate_invocation_list(triple_arch, action, source, config, env):
    """ Generates the invocation for the source file of the current
    compilation command. Used during on-demand analysis. The invocation list
    is a mapping from absolute paths of the source files to the parts of the
    compilation commands that are used to generate from each one of them. """

    triple_arch_dir = Path(config.ctu_dir, triple_arch)
    # Ensure, that architecture directory exists.
    triple_arch_dir.mkdir(parents=True, exist_ok=True)

    invocation_list = triple_arch_dir / 'invocation-list.yml'

    source_path = Path(source).resolve()

    cmd = ctu_triple_arch.get_compile_command(action, config, source)
    # __clang__analyzer__ macro needs to be set in the imported TUs too.
    cmd.extend(['-D__clang_analyzer__', '-w'])

    # The YAML mapping entry already has a newline at the end.
    # Line width is set to max int size because of compatibility with the YAML
    # parser of LLVM. We try to ensure that no lines break in the textual
    # representation of the list items.
    invocation_line = yaml.dump({str(source_path): cmd}, width=maxsize)

    LOG.debug_analyzer("Appending invocation list item '%s'", invocation_line)

    # Append the next entry into the invocation list yaml.
    with invocation_list.open('a', encoding='utf-8', errors='ignore') as \
            invocation_file:
        invocation_file.write(invocation_line)


def generate_ast(triple_arch, action, source, config, env):
    """ Generates ASTs for the current compilation command. Used during
    ast-dump based analysis. """

    cmd, ast_dir = generate_ast_cmd(action, config, triple_arch, source)

    if not os.path.isdir(ast_dir):
        try:
            os.makedirs(ast_dir)
        except OSError:
            pass

    cmdstr = ' '.join(cmd)
    LOG.debug_analyzer("Generating AST using '%s'", cmdstr)
    ret_code, _, err = \
        analyzer_base.SourceAnalyzer.run_proc(cmd, env, action.directory)

    if ret_code != 0:
        LOG.error("Error generating AST.\n\ncommand:\n\n%s\n\nstderr:\n\n%s",
                  cmdstr, err)


def ast_dump_path(source_path):
    """ AST-dump based analysis uses preprocessed paths, here the path prefix
    'ast' and the filename suffix '.ast' is added to the name of the original
    source file. """

    # Normalize path on Windows OS.
    path = os.path.splitdrive(source_path)[1]
    # Make relative path out of absolute.
    path = path[1:] if path[0] == os.sep else path
    # Prepend path segment, and append filename suffix.
    return os.path.join("ast", path + ".ast")


def func_map_list_src_to_ast(func_src_list, ctu_on_demand):
    """ Turns textual function map list with source files into a
    mapping from mangled names to mapped paths, which can be absolute paths to
    the original source files if ctu_on_demand is True, or relative path
    segments to AST-dump files that reside in CTU-DIR directory otherwise. """

    func_ast_list = []
    for fn_src_txt in func_src_list:
        dpos = fn_src_txt.find(" ")
        mangled_name = fn_src_txt[0:dpos]
        path = fn_src_txt[dpos + 1:]

        # On-demand analysis does not require any preprocessing on the source
        # file paths, contrary to AST-dump based.
        mapped_path = path if ctu_on_demand else ast_dump_path(path)

        func_ast_list.append(mangled_name + " " + mapped_path)
    return func_ast_list


def get_extdef_mapping_cmd(action, config, source, func_map_cmd):
    """ Get command to create CTU index file. """

    cmd = ctu_triple_arch.get_compile_command(action, config)
    cmd[0] = func_map_cmd
    cmd.insert(1, source)
    cmd.insert(2, '--')
    return cmd


def map_functions(triple_arch, action, source, config, env,
                  func_map_cmd, temp_fnmap_folder):
    """ Generate function map file for the current source.

        On-demand CTU analysis requires the *mangled name* to *source file*
        mapping. However in case of pre-processed ast-dumps, *mangled name* to
        *ast dump* mapping must be provided.
    """

    cmd = get_extdef_mapping_cmd(action, config, source, func_map_cmd)

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
    func_ast_list = func_map_list_src_to_ast(
        func_src_list, config.ctu_on_demand)
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
