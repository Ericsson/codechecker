#!/usr/bin/env python3
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import argparse
import json
import logging
import multiprocessing
import os
import re
import shlex
import shutil
import stat
import subprocess as sp
import sys
import zipfile

import prepare_all_cmd_for_ctu as prepare_cmds

HANDLER = logging.StreamHandler()
FORMATTER = logging.Formatter('[%(levelname)s %(asctime)s] - %(message)s',
                              '%Y-%m-%d %H:%M')
HANDLER.setFormatter(FORMATTER)

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
LOG.addHandler(HANDLER)


class ReduceOptions:
    """
    Holds information about the reduction process that is constant
    for a given CTU analyze command.
    """
    def __init__(self,
                 analyzed_file,
                 analyze_sh,
                 analyze_std,
                 assert_string,
                 clang,
                 jobs,
                 compilation_db):
        self.analyzed_file = analyzed_file
        self.analyze_sh = analyze_sh
        self.analyze_std = analyze_std
        self.assert_string = assert_string
        self.clang = clang
        self.jobs = jobs
        self.compilation_db = compilation_db


def get_std_flag(cmd):
    """
    Get the C/C++ standard from a compilation command string.
    """
    pattern = re.compile("-std=")
    cmd_list = shlex.split(cmd)
    for element in cmd_list:
        if pattern.match(element):
            return element
    return ""


def run_ctu_collect(compile_cmd_file, jobs, work_dir):
    """
    Run the collect phase of the CodeChecker CTU analysis process.
    """
    env = {**os.environ, 'LD_LIBRARY_PATH': '""'}
    cmd = ["CodeChecker", "analyze", "--ctu-collect", "--compiler-info-file",
           os.path.join(work_dir, "compiler_info_DEBUG.json"),
           compile_cmd_file, "-o", "report-debug", "-j", str(jobs)]
    prepare_cmds.execute(cmd, env=env)


def is_cpp_or_c_file(file_name):
    """
    Check if the given file is a C or C++ source file.
    """
    pattern = re.compile(r'\.(c|cc|cp|cpp|c\+\+|cxx|C|CPP)')
    _, extension = os.path.splitext(file_name)
    return pattern.search(extension)


def get_assert_string(repro_zip):
    """
    Peek into the given ZIP file and find the assertion message of the
    CTU analysis crash.
    """
    stderr = ''
    with zipfile.ZipFile(repro_zip) as cc_zip:
        with cc_zip.open('stderr', 'r') as err:
            stderr = err.read().decode('utf-8')
    pattern = re.compile(r"Assertion[\s\S]+failed.(?=\nStack)")
    match = pattern.search(stderr)
    if not match:
        return ""
    return match.group()


def get_ast_dump_cmd(clang, std_flag, reduced_file, triple_arch):
    """
    Construct the command that will regenerate the AST dump of the given
    dependent file.
    """
    work_dir = os.path.dirname(reduced_file)
    ast_dump_path = os.path.join(os.path.join(work_dir, 'report-debug'),
                                 'ctu-dir', triple_arch, 'ast')
    # If one component in os.path.join() is an absolute path, all previous
    # components are thrown away and the joining continues from that component.
    # Hack: add '.' to the beginning of the second component.
    ast_dump_path = os.path.join(ast_dump_path, '.' + reduced_file + '.ast')
    LOG.info("AST dump path: %s", ast_dump_path)
    return [clang, std_flag, '-Xclang', '-emit-pch', '-o', ast_dump_path, '-c',
            reduced_file]


def get_failing_cmd(cmd_file, file_path):
    """
    Reconstruct the failing CTU analysis command from the SH file and
    a path to the relocated analyzed file.
    """
    with open(cmd_file, 'r') as analyze_cmd_file:
        ctu_analyze_fail_cond = analyze_cmd_file.read().split(" ")
    ctu_analyze_fail_cond[-1] = file_path
    return ctu_analyze_fail_cond


def try_empty(test_script, reduced_file):
    """
    Before running the lengthy C-Reduce process, check if an empty version
    of the dependent file satisfies the interestingness test.
    """
    backup = reduced_file + '.orig'
    try:
        shutil.copyfile(reduced_file, backup)
    except OSError:
        LOG.info("Could not backup file %s", reduced_file)
        return 1

    # Delete contents of the .cpp file.
    open(reduced_file, "w").close()

    log_file = os.path.join(os.path.dirname(reduced_file), 'reduce.log')
    with open(log_file, "a") as log:
        proc = sp.run([test_script], stdin=sp.PIPE, stdout=log, stderr=log,
                      universal_newlines=True)

    if proc.returncode:
        LOG.info("Empty file failes test")
        os.rename(backup, reduced_file)
        return 2

    LOG.info("Empty file passes test")
    os.remove(backup)
    return 0


def run_creduce(reduced_file, test_script, num_threads, counter=1):
    """
    Run C-Reduce on the specified file with the given interestingness test.
    """
    if counter < 1:
        failed = try_empty(test_script, reduced_file)
        if not failed:
            return

    # FIXME: Is there a need to specify custom creduce commands?
    # Maybe optinally read it from a file?
    cmd = ['creduce', test_script, reduced_file, '--n', str(num_threads),
           '--timeout', '30', '--timing', '--debug',
           '--no-default-passes', '--add-pass', 'pass_lines', '0', '410']
    log_file = os.path.join(os.path.dirname(reduced_file),
                            "reduce_%s.log" % os.path.basename(reduced_file))
    with open(log_file, "a") as log:
        sp.run(cmd, stdout=log, stderr=log, universal_newlines=True,
               cwd=os.path.dirname(reduced_file))
        check = sp.run([test_script], stdout=log, stderr=log,
                       universal_newlines=True)
        if check.returncode != 0:
            # C-Reduce left the file in a state when the test fails.
            # Recover by changing the 'orig' file back to 'cpp'.
            os.rename(reduced_file + '.orig', reduced_file)


def dump_test(conditions, reduced_file):
    """
    Write the interestingness test conditions into an executable SH file.
    Return the absolute path to the file.
    """
    test_script = \
        os.path.join(os.path.dirname(reduced_file),
                     'creduce_test_%s.sh' % os.path.basename(reduced_file))

    with open(test_script, 'w') as test:
        test.write("#!/bin/bash\n\n")
        # FIXME: Does this work for all kinds of creduce installations?
        # If not, we might need a way to configure it. Maybe a JSON file?
        test.write("LD_LIBRARY_PATH=''\n\n")
        test.write(' '.join(conditions))
    status = os.stat(test_script)
    os.chmod(test_script, status.st_mode | stat.S_IEXEC)

    return test_script


def assemble_test(reduced_file, opts, std_flag):
    """
    Assemble the interestingness test for the file currently being reduced.
    This is a bash script that C-Reduce uses to verify whether the current
    state of a file still reproduces the investigated behavior. If it does,
    the script needs to exit with 0, otherwise with some other value.
    It is important that the test exists with 0 before reduction begins.

    Arguments:
        reduced_file : absolute path to the file currently being reduced,
        opts         : a ReduceOptions type object containing non-variable
                       information about the reduction process like the
                       assertion string; paths to the analyzed file, the
                       analyzer command, and the clang binary; etc.

    Returns a list of commands that will be written to a bash script file.
    Each command is a list itself, divided along spaces.
    """
    conditions = []
    ending = ['2>&1', '&&\\\n']
    is_dependent = (reduced_file != opts.analyzed_file)

    # Ensure that the file is compilable, then clean up.
    object_file = os.path.splitext(reduced_file)[0] + '.o'
    conditions.extend([opts.clang, '-c', std_flag, reduced_file,
                       '-o', object_file, '>/dev/null'] + ending)
    conditions.extend(['rm', object_file, '>/dev/null'] + ending)

    if is_dependent:
        # Re-generate AST in "workspace"/report-debug/ctu-dir.
        triple_arch = prepare_cmds.get_triple_arch(opts.analyze_sh)
        conditions.extend(get_ast_dump_cmd(opts.clang, std_flag,
                                           reduced_file, triple_arch))
        conditions.extend(['>/dev/null'] + ending)

    # Add negation of the failing analyzer command.
    failing_cmd = get_failing_cmd(opts.analyze_sh, opts.analyzed_file)
    err_dest = os.path.join(os.path.dirname(reduced_file), 'crash.txt')
    conditions.extend(['!'] + failing_cmd + ['>' + err_dest] + ending)

    # Ensure that the previous command still produces the assertion.
    assert_string = opts.assert_string.replace('\"', '\\\"') \
                                      .replace('`', '\\`')   \
                                      .replace('!', '\\!')
    conditions.extend(['grep', '\"' + assert_string + '\"',
                       err_dest, '>/dev/null', '2>&1'])

    return dump_test(conditions, reduced_file)


def reduce_iteration(opts, cmds, counter, work_dir):
    """
    Go through all source files in the ZIP, running one round of C-Reduce
    on them. Start with dependent files. Before running C-Reduce, check
    if an empty version of a file satisfies the interestingness test.
    """
    LOG.info('Starting to reduce dependent files.')
    for cmd in cmds:
        if not is_cpp_or_c_file(cmd['file']) or \
           cmd['file'] == opts.analyzed_file:
            continue
        std_flag = get_std_flag(cmd['command'])
        if os.stat(cmd['file']).st_size > 0:
            LOG.info('Reducing dependent file: %s', cmd['file'])
            test = assemble_test(cmd['file'], opts, std_flag)
            run_creduce(cmd['file'], test, opts.jobs, counter)
            run_ctu_collect(opts.compilation_db, opts.jobs, work_dir)

    LOG.info('Starting to reduce analyzed file: %s', opts.analyzed_file)
    test = assemble_test(opts.analyzed_file, opts, opts.analyze_std)
    run_creduce(opts.analyzed_file, test, opts.jobs, counter)


def get_cmd_after_preproc(old_cmd, file_dir_path):
    """
    Create a new compilation command for a preprocessed and relocated
    source file.
    """
    old_cmd = __remove_dependency_generation(shlex.split(old_cmd))
    new_cmd = []
    param_pattern = re.compile("-I|-D|-isystem")
    for element in old_cmd:
        if param_pattern.match(element):
            continue
        new_cmd.append(element)

    obj_ind = new_cmd.index('-o')
    new_cmd[obj_ind + 1] = \
        os.path.join(file_dir_path,
                     os.path.basename(old_cmd[old_cmd.index('-o') + 1]))

    file_name = os.path.basename(old_cmd[-1])
    new_cmd[-1] = os.path.join(file_dir_path, file_name)
    new_cmd = ' '.join(new_cmd)
    LOG.info("Updated compile command: %s", new_cmd)
    return new_cmd


def get_new_analyzer_cmd(clang, old_cmd, output_dir, triple_arch):
    """
    Create a new CTU analyze command after files have been relocated
    and modified for debugging.
    """
    old_cmd = shlex.split(old_cmd)
    new_cmd = []
    param_pattern_include = re.compile("-I|-D")
    param_pattern2 = re.compile("-isystem")
    corresp = False
    for element in old_cmd:
        if param_pattern_include.match(element):
            continue
        if param_pattern2.match(element):
            corresp = True
            continue
        if corresp:
            corresp = False
            continue
        if re.match("ctu-dir", element):
            new_cmd.append(
                'ctu-dir=' +
                os.path.join(
                    output_dir,
                    'report-debug',
                    'ctu-dir',
                    triple_arch))
            continue
        else:
            new_cmd.append(element)

    file_name = os.path.basename(old_cmd[-1])
    new_cmd[-1] = os.path.join(output_dir, file_name)
    new_cmd[0] = clang
    new_cmd.insert(2, '-Werror=odr')
    return ' '.join(new_cmd)


def __eliminate_argument(arg_vect, opt_string, has_arg=False):
    """
    This call eliminates the parameters matching the given option string,
    along with its argument coming directly after the opt-string if any,
    from the command. The argument can possibly be separated from the flag.
    """
    while True:
        option_index = next(
            (i for i, c in enumerate(arg_vect)
             if c.startswith(opt_string)), None)

        if option_index:
            separate = 1 if has_arg and \
                len(arg_vect[option_index]) == len(opt_string) else 0
            arg_vect = arg_vect[0:option_index] + \
                arg_vect[option_index + separate + 1:]
        else:
            break

    return arg_vect


def __remove_dependency_generation(command):
    """
    Remove dependency generating flags from the compilation command.
    Expects command as a list and returns a modified list.
    """
    command = __eliminate_argument(command, '-MM')
    command = __eliminate_argument(command, '-MF', True)
    command = __eliminate_argument(command, '-MP')
    command = __eliminate_argument(command, '-MT', True)
    command = __eliminate_argument(command, '-MQ', True)
    command = __eliminate_argument(command, '-MD')
    command = __eliminate_argument(command, '-MMD')
    command = __eliminate_argument(command, '-MJ', True)
    command = __eliminate_argument(command, '-MV')
    return command


def get_preprocess_cmd(comp_cmd, repro_dir, filename, clang_path):
    """
    From a gcc compile command in string format, create a
    clang preprocessing command in list format.
    """
    preproc_cmd = __remove_dependency_generation(comp_cmd.split(' '))
    preproc_cmd[0] = clang_path
    preproc_cmd.insert(1, '-E')

    out_ind = preproc_cmd.index('-o')
    preproc_cmd[out_ind + 1] = os.path.join(repro_dir, filename)

    # FIXME: CodeChecker API that converts a gcc cmd to a clang cmd?
    if '-Wno-maybe-uninitialized' in preproc_cmd:
        preproc_cmd.remove('-Wno-maybe-uninitialized')

    return preproc_cmd


def preprocess(cmd, output_dir, clang):
    """
    Assemble and run the preprocessing command for a given compilation command.
    """
    preproc_cmd = get_preprocess_cmd(cmd['command'],
                                     output_dir,
                                     os.path.basename(cmd['file']),
                                     clang)
    prepare_cmds.execute(preproc_cmd, cwd=cmd['directory'])


def save_new_analyzer_cmd(output_dir, args):
    """
    Save new CTU analyze command for the debug environment into a file.
    """
    analyze_sh = os.path.join(output_dir, 'analyze.sh')
    with open(args.analyzer_command, 'r') as old:
        with open(analyze_sh, 'w') as new:
            triple_arch = prepare_cmds.get_triple_arch(old.name)
            new_cmd = get_new_analyzer_cmd(args.clang, old.read(),
                                           output_dir, triple_arch)
            analyzed_file = new_cmd.split(" ")[-1]
            analyze_std_flag = get_std_flag(new_cmd)
            new.write(new_cmd)

    status = os.stat(analyze_sh)
    os.chmod(analyze_sh, status.st_mode | stat.S_IEXEC)
    return analyze_sh, analyzed_file, analyze_std_flag


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Reduces reproduction files for CTU assertions '
        'based on the repro zip file generated by CodeChecker. '
        'This script requires CodeChecker to be added to PATH '
        'and its environment sourced. You can specify which Clang to use '
        '(it is taken from PATH by default).')

    parser.add_argument(
        'repro_zip',
        metavar="ZIP",
        help='A .zip file containing files needed for reproduction '
             '(generated by CodeChecker).')
    parser.add_argument(
        '-j', '--jobs',
        metavar="N",
        type=int, dest="jobs",
        default=multiprocessing.cpu_count(),
        help='Number of threads to be used for main file reduction.')
    parser.add_argument(
        '-o', '--output',
        metavar="DIR",
        dest='o',
        default='./ctu-repro-dir',
        help="Destination directory to hold reduced repro files.")
    parser.add_argument(
        '--analyzer-command',
        metavar="FILE",
        default='./analyzer-command_DEBUG',
        help='Path to a script with the erroneous analyzer call.')
    parser.add_argument(
        '--sources-root',
        metavar="PATH",
        default='./sources-root',
        help='Path to the sources-root directory.')
    parser.add_argument(
        '--report-dir',
        metavar="PATH",
        default='..',
        help="Path to the report dir.")
    parser.add_argument(
        '--clang',
        metavar="PATH",
        default=None,
        help="Path to the clang binary.")
    parser.add_argument(
        '--clang-plugin-name',
        metavar="NAME",
        default=None,
        help="Name of the used clang plugin.")
    parser.add_argument(
        '--clang-plugin-path',
        metavar="PATH",
        default=None,
        help="Path to the used clang plugin.")
    parser.add_argument(
        '--continue-reduce',
        action='store_true',
        help="Continue the previous run of this script.")

    return parser.parse_args()


def check_environment(clang):
    """
    Check whether the required binaries are available.
    """
    cc_binary = shutil.which('CodeChecker')
    if cc_binary is None:
        LOG.error('CodeChecker not found! Check your PATH.')
        sys.exit(-1)
    LOG.info('Using CodeChecker: %s', cc_binary)

    creduce_binary = shutil.which('creduce')
    if creduce_binary is None:
        LOG.error('C-Reduce not found! Check your PATH.')
        sys.exit(-1)
    LOG.info('Using C-Reduce: %s', creduce_binary)

    if clang is not None:
        clang = os.path.abspath(clang)
        os.environ['PATH'] = os.path.dirname(clang) + \
            os.pathsep + os.environ['PATH']
        LOG.info('Using Clang: %s', clang)
    else:
        clang = shutil.which('clang')
        if not clang:
            LOG.error('Clang not found! Check your PATH.')
            sys.exit(-1)
        LOG.info('Using Clang from PATH: %s', clang)
    return clang


def main():
    args = parse_arguments()

    repro_zip = os.path.abspath(args.repro_zip)
    LOG.info("Using zip file: %s", repro_zip)

    work_dir = os.path.dirname(repro_zip)
    output_dir = os.path.abspath(args.o)

    assert_string = get_assert_string(repro_zip)
    if not assert_string:
        LOG.error('Assert string not found!')
        return
    LOG.info('Assert string found: %s', assert_string)

    args.clang = check_environment(args.clang)

    if not args.continue_reduce:
        LOG.info("Creating output directory: %s", output_dir)
        try:
            os.mkdir(output_dir)
        except OSError:
            LOG.error('Output directory already exists!')
            return

        os.chdir(work_dir)

        with zipfile.ZipFile(repro_zip) as cc_zip:
            try:
                cc_zip.extractall('.')
            except zipfile.BadZipFile:
                LOG.error('ZIP extraction has failed')
                return
        LOG.info('Repro files unzipped')

        LOG.info('Preparing commands for reproduction')
        path_options = prepare_cmds.PathOptions(
            args.sources_root,
            args.clang,
            args.clang_plugin_name,
            args.clang_plugin_path,
            args.report_dir)
        prepare_cmds.prepare(args.jobs, path_options, collect=False)
        compile_cmds = json.load(open(os.path.join(work_dir,
                                                   'compile_cmd_DEBUG.json')))

        LOG.info('Preprocessing files')
        for cmd in compile_cmds:
            if not is_cpp_or_c_file(cmd['file']):
                continue

            preprocess(cmd, output_dir, args.clang)

            cmd['directory'] = output_dir
            cmd['file'] = os.path.join(output_dir,
                                       os.path.basename(cmd['file']))
            cmd['command'] = get_cmd_after_preproc(cmd['command'], output_dir)

        LOG.info('Files preprocessed')

        LOG.info('Assembling new compilation commands')
        compile_cmds = {x['command']: x for x in compile_cmds}.values()
        compile_cmds_json = os.path.join(output_dir, 'compile_commands.json')
        with open(compile_cmds_json, 'w') as commands_json:
            commands_json.write(json.dumps(list(compile_cmds), indent=4))

        LOG.info('New compile commands file created at %s', compile_cmds_json)

        LOG.info('Creating new analyzer command file')
        analyze_sh, analyzed_file, analyze_std_flag = \
            save_new_analyzer_cmd(output_dir, args)
        LOG.info('New analyzer command file created at %s', analyze_sh)

    else:
        analyze_sh = os.path.join(output_dir, 'analyze.sh')
        with open(analyze_sh, 'r') as cc_analyze_cmd_file:
            cmd = cc_analyze_cmd_file.read()
            analyze_std_flag = get_std_flag(cmd)
            analyzed_file = cmd.split(" ")[-1]

        compile_cmds_json = os.path.join(output_dir, 'compile_commands.json')
        compile_cmds = json.load(open(compile_cmds_json))

    os.chdir(output_dir)

    LOG.info('Creating CTU dir at %s', os.path.join(output_dir,
                                                    'report-debug'))
    run_ctu_collect(compile_cmds_json, args.jobs, work_dir)
    opts = ReduceOptions(analyzed_file, analyze_sh, analyze_std_flag,
                         assert_string, args.clang, args.jobs,
                         compile_cmds_json)

    old_size = os.stat(analyzed_file).st_size
    LOG.info('Size of analyzed file: %d', old_size)
    counter = 0
    while True:
        reduce_iteration(opts, compile_cmds, counter, work_dir)
        new_size = os.stat(analyzed_file).st_size
        LOG.info('Analyzed file size: %s', new_size)
        if new_size >= old_size:
            break
        old_size = new_size
        counter += 1

    LOG.info("Reduced test cases can be found under %s", output_dir)


if __name__ == "__main__":
    main()
