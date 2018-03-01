#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
import argparse
import re
import os
import shutil
import stat
import json
import contextlib
import io
import sys
import subprocess
import multiprocessing
import prepare_all_cmd_for_ctu


# Suppressing output of functions
class DummyFile(object):
    def write(self, x): pass


@contextlib.contextmanager
def nostdout():
    save_stdout = sys.stdout
    sys.stdout = DummyFile()
    yield
    sys.stdout = save_stdout


def get_analyzed_file_path(analyzer_command_file):
    with open(analyzer_command_file, 'r') as f:
        return f.read().split(" ")[-1]


def get_std_flag(str):
    std_flag_pattern = re.compile("-std=")
    l = str.split()
    for x in l:
        if std_flag_pattern.match(x):
            return x
    return ""


def create_ctu_dir(compile_cmds_file):
    prepare_all_cmd_for_ctu.execute(["CodeChecker", "analyze", "--ctu-collect",
                                     compile_cmds_file, "-o", "cc_files"],
                                    False)


def isCppOrCFile(file_name):
    c_pattern = re.compile('\.c$|\.cpp$|\.cxx$')
    return c_pattern.search(file_name)


def get_assertion_string(analyzer_command_file):
    error = subprocess.Popen(["bash", analyzer_command_file],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, error_string = error.communicate()
    assert_pattern = re.compile('Assertion.+failed\.')
    assert_match = assert_pattern.search(error_string)
    if not assert_match:
        return ""
    return assert_match.group(0)


def get_compilable_cond(clang, stdflag, file_name):
    return [clang, '-c', '-Werror', stdflag, file_name]


def get_ast_dump_cond(clang, stdflag, file_abs_path, file_name, triple_arch):
    ast_dump_path = os.path.join(os.path.abspath('./cc_files'),
                                 'ctu-dir', triple_arch, 'ast')
    ast_dump_path = os.path.join(ast_dump_path, '.' + file_abs_path + '.ast')
    return [clang, stdflag, '-Xclang', '-emit-pch', '-o', ast_dump_path, '-c',
            file_name]


def get_normal_analyze_cond(ctu_analyze_fail_cond):
    normal_analyze_cond = []
    ctu_pattern = re.compile("xtu|ctu|analyzer-config")
    for x in ctu_analyze_fail_cond:
        if not ctu_pattern.search(x):
            normal_analyze_cond.append(x)
        else:
            normal_analyze_cond = normal_analyze_cond[:-1]
    return normal_analyze_cond


def get_ctu_analyze_fail_cond(cmd_file, file_path):
    with open(cmd_file, 'r') as f:
        ctu_analyze_fail_cond = f.read().split(" ")
    ctu_analyze_fail_cond[-1] = file_path
    return ctu_analyze_fail_cond


def add_assert_cond(ctu_analyze_fail_cond, assert_string):
    assert_string = assert_string.replace('\"', '\\\"').replace('`', '\\`')
    match_condition = ['grep', '-F', '\"' + assert_string + '\"']
    piping = ['2>&1', '>/dev/null', '|']
    ctu_analyze_fail_cond.extend(piping)
    ctu_analyze_fail_cond.extend(match_condition)
    return ctu_analyze_fail_cond


def run_creduce(conditions, file_to_reduce, num_threads):
    # writing the test script for creduce
    creduce_test_name = 'creduce_test.sh'
    with open(creduce_test_name, 'w') as test:
        test.write("#!/bin/bash\n")
        test.write(' >/dev/null 2>&1 &&\\\n'.join(conditions))
    # make it executable
    st = os.stat(creduce_test_name)
    os.chmod(creduce_test_name, st.st_mode | stat.S_IEXEC)
    subprocess.call(['creduce', creduce_test_name,
                     file_to_reduce, '--n', str(num_threads)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def reduce_main(reduce_file_name, assert_string, analyzer_command_file,
                num_threads, clang, stdflag):
    conditions = []
    compilable_cond = get_compilable_cond(clang, stdflag, reduce_file_name)
    conditions.append(' '.join(compilable_cond))

    ctu_analyze_fail_cond = get_ctu_analyze_fail_cond(analyzer_command_file,
                                                      reduce_file_name)
    normal_analyze_cond = get_normal_analyze_cond(ctu_analyze_fail_cond)
    conditions.append(' '.join(normal_analyze_cond))

    ctu_analyze_fail_cond = add_assert_cond(
        ctu_analyze_fail_cond, assert_string)
    conditions.append(' '.join(ctu_analyze_fail_cond))

    run_creduce(conditions, reduce_file_name, num_threads)


def reduce_dep(dep_file_abs_path, assert_string,
               analyzer_command_file, reduced_main_file_name, clang, stdflag):
    reduce_file_name = os.path.basename(dep_file_abs_path)

    conditions = []
    compilable_cond = get_compilable_cond(clang, stdflag, reduce_file_name)
    conditions.append(' '.join(compilable_cond))
    prepare_all_cmd_for_ctu.get_triple_arch(analyzer_command_file)
    ast_dump_cond = get_ast_dump_cond(
        clang, stdflag, dep_file_abs_path, reduce_file_name, triple_arch)
    conditions.append(' '.join(ast_dump_cond))

    ctu_analyze_fail_cond = get_ctu_analyze_fail_cond(
        analyzer_command_file, os.path.abspath(reduced_main_file_name))
    ctu_analyze_fail_cond = add_assert_cond(
        ctu_analyze_fail_cond, assert_string)
    conditions.append(' '.join(ctu_analyze_fail_cond))

    run_creduce(conditions, reduce_file_name, 1)


def get_new_cmd(old_cmd, file_dir_path):
    old_cmd = old_cmd.split(" ")
    new_cmd = []
    param_pattern = re.compile("-I|-D|-isystem")
    for x in old_cmd:
        if param_pattern.match(x):
            continue
        new_cmd.append(x)

    obj_ind = new_cmd.index('-o')
    new_cmd[obj_ind + 1] = \
        os.path.join(file_dir_path,
                     os.path.basename(old_cmd[old_cmd.index('-o') + 1]))

    file_name = os.path.basename(old_cmd[-1])
    new_cmd[-1] = os.path.join(file_dir_path, file_name)
    return ' '.join(new_cmd)


def get_new_analyzer_cmd(clang, old_cmd, file_dir_path, triple_arch):
    old_cmd = old_cmd.split(" ")
    new_cmd = []
    param_pattern_include = re.compile("-I|-D")
    param_pattern2 = re.compile("-isystem")
    corresp = False
    for x in old_cmd:
        if param_pattern_include.match(x):
            continue
        if param_pattern2.match(x):
            corresp = True
            continue
        if corresp:
            corresp = False
            continue
        if re.match("xtu-dir", x):
            new_cmd.append(
                'xtu-dir=' +
                os.path.join(
                    file_dir_path,
                    'cc_files',
                    'ctu-dir',
                    triple_arch))
            continue
        else:
            new_cmd.append(x)

    file_name = os.path.basename(old_cmd[-1])
    new_cmd[-1] = os.path.join(file_dir_path, file_name)
    new_cmd[0] = clang
    new_cmd.insert(2, '-Werror=odr')
    return ' '.join(new_cmd)


def get_preprocess_cmd(comp_cmd, repro_dir, filename):
    preproc_cmd = str(comp_cmd.decode("utf-8")).split(' ')
    preproc_cmd = filter(lambda x: not re.match('-c', x), preproc_cmd)
    preproc_cmd.insert(1, '-E')
    out_ind = preproc_cmd.index('-o')
    preproc_cmd[out_ind + 1] = os.path.join(repro_dir, filename)
    return preproc_cmd


def main():
    parser = argparse.ArgumentParser(
        description='Reduces the reproduction files for CTU assertions '
        '(assertions only!) based on the repro zip file which is generated '
        'by CodeChecker. This script requires CodeChecker set added to PATH '
        'and its environment sourced. Clang is neccessary as well, you can, '
        'you can specify which one to use (it is taken from PATH by default). '
        'You must provide the repro zip path and the ')
    parser.add_argument(
        '--analyzer-command',
        default='./analyzer-command_DEBUG',
        help='Path of the script which calls the analyzer '
             'resulting a CTU error.')
    parser.add_argument(
        '-j',
        default=multiprocessing.cpu_count(),
        help='Number of threads for the reduce of the '
             'main file.')
    parser.add_argument(
        '--verbose',
        default=False,
        action='store_true',
        help='Verbose mode.')
    parser.add_argument(
        '--sources_root',
        default='./sources-root',
        help='Path of the source root.')
    parser.add_argument(
        '--report_dir',
        default='..',
        help="Path of the report dir.")
    parser.add_argument(
        '--clang',
        default=None,
        help="Path to the clang binary.")
    parser.add_argument(
        '--clang_plugin_name',
        default=None,
        help="Name of the used clang plugin.")
    parser.add_argument(
        '--clang_plugin_path',
        default=None,
        help="Path to the used clang plugin.")
    parser.add_argument(
        '--repro_zip',
        default=None,
        required=True,
        help='The zip which contains the files needed for reproduction '
             '(generated by CodeChecker).')
    parser.add_argument(
        '-o', default='./bug_repro_dir',
        help='The output dir which contains the reduced files '
             'reproducing the bug.')
    args = parser.parse_args()
    # change the paths to absolute
    repro_zip = os.path.abspath(args.repro_zip)
    output_dir = os.path.abspath(args.o)

    print('Reduce script running started.')
    if args.clang is not None:
        args.clang = os.path.abspath(args.clang)
        os.environ['PATH'] = os.path.dirname(args.clang) + \
            os.pathsep + os.environ['PATH']
        if args.verbose:
            print('using clang: ' + args.clang)
    else:
        args.clang = 'clang'
        if args.verbose:
            print('using clang from PATH')

    pathOptions = prepare_all_cmd_for_ctu.PathOptions(
        args.sources_root,
        args.clang,
        args.clang_plugin_name,
        args.clang_plugin_path,
        args.report_dir)

    if args.verbose:
        print("Creating output directory: " + output_dir)
    try:
        os.mkdir(output_dir)
    except OSError:
        print('error: Repro dir already exist!')
        return

    analyzer_command_file = os.path.join(output_dir, 'analyze.sh')

    # unzip
    os.chdir(os.path.dirname(repro_zip))
    args.sources_root = os.path.abspath(args.sources_root)
    if args.verbose:
        print("Reducing test case from zip file: " + repro_zip)

    for file_name in os.listdir(os.getcwd()):
        if 'zip' in file_name or os.path.basename(output_dir) == file_name:
            continue
        if os.path.isfile(file_name):
            os.remove(file_name)
        else:
            shutil.rmtree(file_name)

    if args.verbose:
        print('unzip reproduction files')
    try:
        output = subprocess.check_output(
            ['timeout', '3', 'unzip', repro_zip], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print('error: unzip command has failed')
        return

    if args.verbose:
        print('Preparing commands for CTU analysis.')
    with nostdout():
        prepare_all_cmd_for_ctu.prepare(pathOptions)

    compile_cmds = json.load(open('./compile_cmd_DEBUG.json'))
    for cmd in compile_cmds:
        file_name = os.path.basename(cmd['file'])
        if not isCppOrCFile(file_name):
            continue
        preproc = subprocess.Popen(
            get_preprocess_cmd(
                cmd['command'],
                output_dir,
                file_name),
            cwd=cmd['directory'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        out, err = preproc.communicate()
        cmd['directory'] = output_dir
        cmd['file'] = os.path.join(output_dir, file_name)
        cmd['command'] = get_new_cmd(cmd['command'], output_dir)

    # uniquing compile_commands
    compile_cmds = {x['command']: x for x in compile_cmds}.values()
    # writing compile commands to output dir
    with open(os.path.join(output_dir, 'compile_commands.json'), 'w') as cc:
        cc.write(json.dumps(compile_cmds, indent=4))
    # writing compile commands to output dir
    with open(args.analyzer_command, 'r') as f:
        with open(analyzer_command_file, 'w') as f2:
            triple_arch = prepare_all_cmd_for_ctu.get_triple_arch(f)
            f2.write(get_new_analyzer_cmd(args.clang, f.read(), output_dir, triple_arch))

    # make it runnable
    st = os.stat(analyzer_command_file)
    os.chmod(analyzer_command_file, st.st_mode | stat.S_IEXEC)

    if args.verbose:
        print('cleanup')
    # cleanup
    for file_name in os.listdir(os.getcwd()):
        if 'zip' in file_name or os.path.basename(output_dir) == file_name:
            continue
        if os.path.isfile(file_name):
            os.remove(file_name)
        else:
            shutil.rmtree(file_name)

    os.chdir(output_dir)
    if args.verbose:
        print('creating ctu dir')
    create_ctu_dir('compile_commands.json')

    assert_string = get_assertion_string(analyzer_command_file)
    if args.verbose:
        print('assert string found: ' + assert_string)
    if not assert_string:
        print('assert string not found!')
        return

    analyzed_file = get_analyzed_file_path(analyzer_command_file)
    analyzed_file_name = os.path.basename(analyzed_file)
    with open(analyzer_command_file, 'r') as f:
        std_flag = get_std_flag(f.read())

    print('Starting to reduce the analyzed file: ' + analyzed_file)
    reduce_main(analyzed_file_name, assert_string,
                analyzer_command_file, args.j, args.clang, std_flag)

    print('Starting to reduce dependent files.')
    cmd_to_remove = set()
    for cmd in compile_cmds:
        file_name = os.path.basename(cmd['file'])
        if not isCppOrCFile(file_name) or file_name == analyzed_file_name:
            continue
        std_flag = get_std_flag(cmd['command'])
        if args.verbose:
            print('Reducing dependent file: ' + cmd['file'])
        reduce_dep(cmd['file'], assert_string, analyzer_command_file,
                   analyzed_file_name, args.clang, std_flag)

        if os.stat(cmd['file']).st_size == 0:
            os.remove(cmd['file'])
            cmd_to_remove.add(cmd['command'])
        else:
            create_ctu_dir("compile_commands.json")

    # remove unnecessary commands from compile_commands_json
    compile_cmds = [
        x for x in compile_cmds if x['command'] not in cmd_to_remove]
    with open(os.path.join(output_dir, 'compile_commands.json'), 'w') as cc:
        cc.write(json.dumps(compile_cmds, indent=4))

    # cleanup from output dir
    for file_name in os.listdir(output_dir):
        if not re.search('.orig$|creduce_test', file_name):
            continue
        print file_name
        assert(os.path.isfile(file_name))
        os.remove(file_name)

    print("Reduced test cases can be found in directory: " + output_dir)


if __name__ == '__main__':
    main()
