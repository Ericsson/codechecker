#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
This script wraps C-Reduce to make it easier to reproduce a minimal example
based on a non-CTU fail zip.
"""
import argparse
import json
import operator
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile


def check_files_existence(report_dir):
    """
    This function checks the existence of some files which are required for the
    reduction process.
    """
    def check(path, isfile):
        if not os.path.isfile(path) if isfile else os.path.isdir(path):
            print('Error: ' + path + " doesn't exist.")
            sys.exit(1)

    check(report_dir, False)
    check(os.path.join(report_dir, 'metadata.json'), True)
    check(os.path.join(report_dir, 'compiler_includes.json'), True)
    check(os.path.join(report_dir, 'compiler_target.json'), True)
    check(os.path.join(report_dir, 'compile_cmd.json'), True)


def check_commands_existence():
    """
    This function checks the existence of some commands which are required for
    the reduction process. A dictionary is returned where the key is the
    command name and the value is its absolute path.
    """
    def get_path(cmd):
        proc = subprocess.Popen(['which', cmd], stdout=subprocess.PIPE)
        return proc.communicate()[0]

    commands = ['CodeChecker', 'creduce', 'clang', 'clang-tidy']

    result = dict()

    for command in commands:
        path = get_path(command).strip()

        if not path:
            print('Error: ' + command + ' command not found.')
            sys.exit(1)

        result[command] = path

    return result


def checker_categories():
    """
    This function returns a set of main checker categories i.e. the first part
    of each checker name.
    """
    checkers_proc = subprocess.Popen(['CodeChecker', 'checkers'],
                                     stdout=subprocess.PIPE)

    checkers, _ = checkers_proc.communicate()
    return set(checker[:checker.replace('.', '-').find('-')]
               for checker in checkers.split())


def get_prepared_analyze_command(report_dir,
                                 workspace_dir,
                                 codechecker,
                                 specific_checker=None):
    """
    This function returns a CodeChecker analyze command based on the original
    one which is stored in the metadata.json file in the report directory.

    report_dir -- The report directory path which is used for the original
        analysis.
    workspace_dir -- The workspace directory which contains the new report
        directory which is used for reduction. The new report directory should
        be a temporary location because its content is rewritten between the
        reduction steps.
    codechecker -- Full path of CodeChecker.
    specific_checker -- For fastening reduction only this checker will be
        enabled and all others will be disabled
    """
    def remove_parameterized_flag(cmd, flag):
        try:
            idx = cmd.index(flag)
            del cmd[idx]  # Remove the flag.
            del cmd[idx]  # Remove its parameter.
            return True
        except ValueError:
            return False

    # --- Get analyzer command from metadata.json --- #

    metadata = os.path.join(report_dir, 'metadata.json')
    compiler_includes = os.path.join(report_dir, 'compiler_includes.json')
    compiler_targets = os.path.join(report_dir, 'compiler_target.json')
    compilation_database = os.path.join(workspace_dir, 'compile_cmd.json')
    output_dir = os.path.join(workspace_dir, 'reports')

    with open(metadata) as metadata_file:
        metadata = json.load(metadata_file)

    analyzer_cmd = metadata['command']
    analyzer_cmd[0] = codechecker

    # --- Change compilation database --- #

    parser = argparse.ArgumentParser()
    parser.add_argument('compilation_database')

    # 2 is for skipping "CodeChecker analyze".
    known, _ = parser.parse_known_args(analyzer_cmd[2:])

    analyzer_cmd.remove(known.compilation_database)
    analyzer_cmd.append(compilation_database)

    # --- Change output dir to a temporary directory --- #

    remove_parameterized_flag(analyzer_cmd, '-o')
    remove_parameterized_flag(analyzer_cmd, '--output')

    analyzer_cmd.extend(['-o', output_dir])

    # --- Change compiler includes and targets file --- #

    remove_parameterized_flag(analyzer_cmd, '--compiler-includes-file')
    remove_parameterized_flag(analyzer_cmd, '--compiler-target-file')

    analyzer_cmd.extend(['--compiler-includes-file', compiler_includes])
    analyzer_cmd.extend(['--compiler-target-file', compiler_targets])

    # --- Always do a clean analysis --- #

    analyzer_cmd.append('--clean')

    # --- Disable all checkers but the required one if needed --- #

    if specific_checker is not None:
        while remove_parameterized_flag(analyzer_cmd, '-e'):
            pass
        while remove_parameterized_flag(analyzer_cmd, '--enable'):
            pass
        while remove_parameterized_flag(analyzer_cmd, '-d'):
            pass
        while remove_parameterized_flag(analyzer_cmd, '--disable'):
            pass

        for category in checker_categories():
            analyzer_cmd.extend(['-d', category])

        analyzer_cmd.extend(['-e', specific_checker])

    return analyzer_cmd


def get_build_command_for_file(compilation_database, filename):
    """
    This function finds the first build action in the compilation database
    which compiles the given source file.
    """
    with open(compilation_database) as comp_db_file:
        build_actions = json.load(comp_db_file)

    collection = map(
        operator.itemgetter('command'),
        filter(lambda ba: ba['file'].endswith(filename), build_actions))

    return next(collection, None)


def dump_preprocessed_build_action(build_command, output):
    """
    This function dumps the preprocessed source code to the given output file.
    """

    if not isinstance(build_command, list):
        build_command = build_command.split()

    build_command.append('-E')

    try:
        build_command[build_command.index('-o') + 1] = output
    except ValueError:
        build_command.extend(['-o', output])

    print(build_command)
    subprocess.Popen(build_command).communicate()


def write_creduce_test_file(analyze_cmd,
                            report_dir,
                            parse_content,
                            output_file):
    """
    This function assembles and writes the test file which describes the
    condition of recuding the source file with CReduce.
    """
    content = '''
#!/usr/bin/env bash
{0}
sed -i 's/, "working_directory": "[^"]*"//' {1}/metadata.json
CodeChecker parse --print-steps {1} | grep '{2}'
'''.format(analyze_cmd, report_dir, parse_content)

    with open(output_file, 'w') as reduce_test_file:
        reduce_test_file.write(content)

    os.chmod(output_file, stat.S_IXUSR | stat.S_IRUSR)


def get_prepared_build_action(workdir, build_action, reduce_file):
    source_file = os.path.join(workdir, reduce_file)
    return {
        'directory': build_action['directory'],
        'command': re.sub(r'[\w\/\.]*' + reduce_file,
                          source_file,
                          build_action['command']),
        'file': source_file}


def main():
    """
    The entry point of the script.
    """
    parser = argparse.ArgumentParser(description='''
    Reduce for a specific bug.

    Given the following arguments this script attempts to create a minimal
    example which still produces a specific CodeChecker finding. Reduction
    steps are accomplished as long as the bug is still observable based on the
    output of CodeChecker parse command.''')
    parser.add_argument('--report_dir', required=True,
                        help='Report directory.')
    parser.add_argument('--reduce_file', required=True,
                        help='The file to reduce.')
    parser.add_argument('--parse_content', required=True,
                        help='Reduce the source as long as it still produces '
                        'a "CodeChecker parse" command output which contains '
                        'this string.')
    parser.add_argument('--specific_checker', required=False, default=None,
                        help='Only this checker will be enabled during the '
                        'reduction.')
    args = parser.parse_args()

    check_files_existence(args.report_dir)
    commands = check_commands_existence()

    try:
        # --- Defining some necessary variables --- #

        temp_workdir = tempfile.mkdtemp()
        old_report_dir = os.path.abspath(args.report_dir)
        new_report_dir = os.path.join(temp_workdir, 'reports')
        old_compilation_database = os.path.join(old_report_dir,
                                                'compile_cmd.json')
        new_compilation_database = os.path.join(temp_workdir,
                                                'compile_cmd.json')
        old_reduce_file = args.reduce_file
        new_reduce_file = os.path.join(temp_workdir, old_reduce_file)
        reduce_test_file = os.path.join(temp_workdir, 'creduce_test.sh')

        os.mkdir(new_report_dir)
        print(temp_workdir)

        # --- Getting and dumping compilation database with one command --- #

        with open(old_compilation_database) as comp_db_file:
            build_actions = json.load(comp_db_file)

        build_actions = filter(lambda ba: ba['file'].endswith(old_reduce_file),
                               build_actions)

        if not build_actions:
            print('No build command found for file ', old_reduce_file)
            sys.exit(1)

        build_action = next(build_actions)

        with open(new_compilation_database, 'w') as comp_db_file:
            prepared_build_action = get_prepared_build_action(temp_workdir,
                                                              build_action,
                                                              old_reduce_file)
            json.dump([prepared_build_action], comp_db_file)

        # --- Assembling analyzer command --- #

        analyze_cmd = get_prepared_analyze_command(old_report_dir,
                                                   temp_workdir,
                                                   commands['CodeChecker'],
                                                   args.specific_checker)
        print(analyze_cmd)

        # --- Write preprocessed build command --- #

        dump_preprocessed_build_action(build_action['command'],
                                       new_reduce_file)

        # --- Write C-Reduce test file and run C-Reduce --- #

        write_creduce_test_file(' '.join(analyze_cmd),
                                new_report_dir,
                                args.parse_content,
                                reduce_test_file)

        subprocess.Popen([commands['creduce'],
                          '--n', '1',
                          reduce_test_file,
                          new_reduce_file], cwd=temp_workdir).communicate()
    finally:
        shutil.rmtree(temp_workdir)


if __name__ == '__main__':
    main()
