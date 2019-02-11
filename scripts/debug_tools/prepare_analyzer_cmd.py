#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import argparse
import re
import failure_lib as lib
import os
import sys


def get_first_line_of_file(fname):
    with open(fname) as f:
        return f.readline()


class AnalyzerCommandPathModifier(object):
    def __init__(self, opts):
        self.opts = opts

    def __call__(self, path):

        if re.search('clang$', path):
            return self.opts.clang

        if self.opts.clang_plugin_name is not None and\
                re.search(self.opts.clang_plugin_name, path):
            if self.opts.clang_plugin_path is None:
                print("clang_plugin_name is in a path, "
                      "but clang_plugin_path is not given in the options")
                sys.exit(-1)
            return self.opts.clang_plugin_path

        if re.search('ctu-dir', path):
            if self.opts.ctu_dir is None:
                print('ctu-dir is in a path, but not in the options!')
                sys.exit(-1)
            return self.opts.ctu_dir

        return os.path.join(
            self.opts.sources_root,
            os.path.normpath(
                path.lstrip(
                    os.path.sep)))


class PathOptions(object):
    def __init__(
            self,
            sources_root,
            clang,
            clang_plugin_name,
            clang_plugin_path,
            ctu_dir):
        self.sources_root = sources_root
        self.clang = clang
        self.clang_plugin_name = clang_plugin_name
        self.clang_plugin_path = clang_plugin_path
        self.ctu_dir = ctu_dir


def prepare(analyzer_command_file, pathOptions):
    res = lib.change_paths(get_first_line_of_file(analyzer_command_file),
                           AnalyzerCommandPathModifier(pathOptions),
                           skip_output=True)

    if '-nobuiltininc' not in res:
        return res

    # Find Clang include path
    clang_include_path = lib.get_resource_dir(pathOptions.clang) + '/include'

    if clang_include_path is None:
        clang_lib_path = os.path.dirname(pathOptions.clang) + '/../lib'
        clang_include_path = ''
        for path, _, files in os.walk(clang_lib_path):
            if 'stddef.h' in files:
                clang_include_path = path
                break

    if clang_include_path is None:
        return res

    return res.replace('-nobuiltininc',
                       '-nobuiltininc -isystem ' + clang_include_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepare analyzer-command '
                                     'to execute in local environmennt.')
    parser.add_argument(
        'analyzer_command_file',
        help="The stored analyzer command.")
    parser.add_argument(
        '--sources_root',
        default='./sources-root',
        help="Path of the source root.")
    parser.add_argument(
        '--ctu_dir',
        default=None,
        help="Path of the used ctu-dir.")
    parser.add_argument(
        '--clang',
        required=True,
        help="Path to the clang binary.")
    parser.add_argument(
        '--clang_plugin_name', default=None,
        help="Name of the used clang plugin.")
    parser.add_argument(
        '--clang_plugin_path', default=None,
        help="Path to the used clang plugin.")
    args = parser.parse_args()

    print(
        prepare(
            args.analyzer_command_file,
            PathOptions(
                args.sources_root,
                args.clang,
                args.clang_plugin_name,
                args.clang_plugin_path,
                args.ctu_dir)))
