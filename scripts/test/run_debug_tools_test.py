# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Test the scripts in debug_tools.
"""


import argparse
import tempfile
import os
import subprocess
import shutil
import re
import sys


PROJ_NAME = "testproject"
VERBOSE = False


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='CodeChecker debug_tools test.',
        epilog='Test using tu_collector to collect all files and analyze the collected files.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-p', '--project',
                        type=str,
                        default='https://github.com/oatpp/oatpp.git',
                        required=False,
                        help="URL of a project to analyze."
                             "Can be a GIT repository or a remote archive.")
    parser.add_argument('-c', '--configure-command',
                        type=str,
                        default='cmake',
                        required=False,
                        help="Command to use for configure (prepare for build) the test project."
                             "Can be a command that is executable in the project's directory or the special value \"cmake\".")
    parser.add_argument('-b', '--build-command',
                        type=str,
                        default='make',
                        required=False,
                        help="Command to use for building the test project.")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Print the output of called commands.")

    return parser.parse_args()

class TestFailed(Exception):
    def __init__(self, message):
        self.message = message

def run_process(args):
    print("Calling: '" + ' '.join(args) + "'")
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', check=True)
    if VERBOSE:
        print(result.stdout)
    return result

def count_log_errors(output):
    return len(re.findall('^\[ERROR ', output, re.MULTILINE))

def test(args):
    file_dir = os.path.dirname(os.path.realpath(__file__))
    debug_tools_dir = os.path.join(os.path.dirname(file_dir), 'debug_tools')
    
    orig_root = tempfile.TemporaryDirectory()
    proj_dir = os.path.join(orig_root.name, PROJ_NAME)
    result_dir = os.path.join(orig_root.name, "result")
    report_dir = os.path.join(result_dir, "reports")
    compile_database = os.path.join(result_dir, "compile_commands.json")
    
    os.chdir(orig_root.name)
    
    print('Using project root directory: ' + orig_root.name)
    
    # Get the testproject.
    if args.project[-4:] == '.git':
        # Clone git repository into directory PROJ_NAME.
        run_process(['git', 'clone', args.project, PROJ_NAME])
    else:
        # Download the file.
        # Assume that it is an archive that contains a single directory at root.
        # Extract the contents and rename the directory into PROJ_NAME.
        run_process(['wget', args.project])
        files = os.listdir()
        shutil.unpack_archive(files[0])
        # Remove downloaded file.
        os.remove(files[0])
        files = os.listdir()
        # Rename the archive root directory.
        os.rename(files[0], PROJ_NAME)
        
    os.chdir(proj_dir)
    os.makedirs(report_dir)
    
    # Build and analyze.
    if args.configure_command == 'cmake':
        os.mkdir("build")
        os.chdir("build")
        run_process(['cmake', '..'])
    else:
        if os.access('./autogen.sh', os.X_OK, follow_symlinks=False):
            run_process(['./autogen.sh'])
        run_process([args.configure_command])
    
    run_process(['CodeChecker', 'log', '-b', args.build_command, '-o', compile_database])
    collect_result = run_process(['CodeChecker', 'analyze', '--analyzers', 'clangsa', '-o', report_dir, '--ctu-collect', compile_database])
    collect_errors = count_log_errors(collect_result.stdout)
    analyze_result = run_process(['CodeChecker', 'analyze', '--analyzers', 'clangsa', '-o', report_dir, '--ctu-analyze', compile_database])
    analyze_errors = count_log_errors(analyze_result.stdout)
    
    # Run tu_collector.
    
    #collect_root = tempfile.TemporaryDirectory()
    collect_root = tempfile.mkdtemp()
    #os.mkdir(collect_root)
    collect_zip = os.path.join(collect_root, 'collect.zip')
    collect_dir = os.path.join(collect_root, 'collect')
    collect_report_dir = os.path.join(collect_root, 'report')
    compile_database_debug = os.path.join(collect_dir, 'compilation_database_DEBUG.json')
    
    print('Using root directory for tu_collector test: ' + collect_root)
    
    run_process(['tu_collector', '-l', compile_database, '-z', collect_zip])
    
    # Remove original directory.
    # This ensures that during analysis of the collected files we can not find the original files.
    # FIXME: Collection of system files is still to be checked. 
    orig_root.cleanup()
    
    os.mkdir(collect_dir)
    os.chdir(collect_dir)
    shutil.unpack_archive(collect_zip)
    
    prepare_compile_cmd_result = run_process([os.path.join(debug_tools_dir, 'prepare_compile_cmd.py'), 'compilation_database.json'])
    compile_database_debug_f = open(compile_database_debug, 'w', encoding='utf-8')
    compile_database_debug_f.write(prepare_compile_cmd_result.stdout)
    compile_database_debug_f.close()
    
    # FIXME: compiler_info.json should be used
    collect_result = run_process(['CodeChecker', 'analyze', '--analyzers', 'clangsa', '-o', collect_report_dir, '--ctu-collect', compile_database_debug])
    collect_errors_after = count_log_errors(collect_result.stdout)
    analyze_result = run_process(['CodeChecker', 'analyze', '--analyzers', 'clangsa', '-o', collect_report_dir, '--ctu-analyze', compile_database_debug])
    analyze_errors_after = count_log_errors(analyze_result.stdout)
    
    if collect_errors_after > collect_errors or analyze_errors_after > analyze_errors:
        msg = ('Number of ERROR log lines during CTU collect in original run: {}, in run on collected files: {}\n'
            'Number of ERROR log lines during CTU analyze in original run: {}, in run on collected files: {}').format(
                collect_errors, collect_errors_after, analyze_errors, analyze_errors_after)
        raise TestFailed(msg)

def main():
    try:
        global VERBOSE
        args = parse_arguments()
        VERBOSE = args.verbose
        test(args)
    except subprocess.CalledProcessError as e:
        print('Command failed')
        if not VERBOSE:
            print('Output:')
            print(e.output)
        sys.exit(1)
    except Exception as e:
        print('ERROR:')
        print(type(e))
        print(e)
        sys.exit(1)

if __name__ == '__main__':
    main()
