import argparse
import re
import os
import shutil
import stat
import subprocess
import multiprocessing


def get_file_path(analyzer_command_file):
    with open(analyzer_command_file, 'r') as f:
        return f.read().split(" ")[-1]


def get_preprocessed_repro_file(abs_file_path, analyzer_command_file):
    with open(analyzer_command_file, 'r') as f:
        cmd = f.read().split(" ")
        param_pattern = re.compile("-I|-D")
        prepoc_params = [x for x in cmd if param_pattern.match(x)]
        preproc = \
            subprocess.Popen(["gcc", "-E"] + prepoc_params + [abs_file_path],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = preproc.communicate()
        filename = abs_file_path.split('/')[-1]
        # assuming exactly one dot (.) in the file name
        prepoc_name = filename.split('.')[0] + "_preproc." + \
            filename.split('.')[1]
    with open(prepoc_name, 'w') as preproc_file:
        preproc_file.write(out)
    return prepoc_name


def get_assertion_string(analyzer_command_file):
    error = subprocess.Popen(["bash", analyzer_command_file],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, error_string = error.communicate()
    assert_pattern = re.compile('Assertion.+failed\.')
    assert_match = assert_pattern.search(error_string)
    if not assert_match:
        return ""
    return assert_match.group(0)


def reduce(prepoc_name, assert_string, analyzer_command_file, num_threads):
    reduce_file_name = prepoc_name.replace("preproc", "reduce")
    if not os.path.exists(reduce_file_name):
        shutil.copy2(prepoc_name, reduce_file_name)
    conditions = []
    compilable_cond = ['gcc', '-c', '-Werror', reduce_file_name]
    conditions.append(' '.join(compilable_cond))
    with open(analyzer_command_file, 'r') as f:
        ctu_analyze_fail_cond = f.read().split(" ")
    ctu_analyze_fail_cond[-1] = reduce_file_name
    ctu_pattern = re.compile("xtu|ctu|analyzer-config")
    normal_analyze_cond = []
    for x in ctu_analyze_fail_cond:
        if not ctu_pattern.search(x):
            normal_analyze_cond.append(x)
        else:
            normal_analyze_cond = normal_analyze_cond[:-1]
    conditions.append(' '.join(normal_analyze_cond))
    if assert_string:
        assert_string = assert_string.replace('\"', '\\\"').replace('`', '\\`')
        match_condition = ['grep', '-F', '\"' + assert_string + '\"']
        piping = ['2>&1', '>/dev/null', '|']
        ctu_analyze_fail_cond.extend(piping)
        ctu_analyze_fail_cond.extend(match_condition)
    conditions.append(' '.join(ctu_analyze_fail_cond))

    creduce_test_name = 'creduce_test.sh'
    with open(creduce_test_name, 'w') as test:
        test.write("#!/bin/bash\n")
        test.write(' >/dev/null 2>&1 &&\\\n'.join(conditions))
    # make it executable
    st = os.stat(creduce_test_name)
    os.chmod(creduce_test_name, st.st_mode | stat.S_IEXEC)
    subprocess.call(['creduce', creduce_test_name,
                     reduce_file_name, '--n', str(num_threads)])


def main():
    parser = argparse.ArgumentParser(
        description='Reduces the reproduction files for CTU bugs.')
    parser.add_argument(
        '--analyzer-command',
        default='./analyzer-command_DEBUG',
        help="Path of the script which calls the analyzer"
             " resulting a CTU error.")
    parser.add_argument(
        '-j',
        default=multiprocessing.cpu_count(),
        help="Number of threads.")
    parser.add_argument(
        '--verbose',
        default=False,
        help="Verbose mode.")
    args = parser.parse_args()

    assert_string = get_assertion_string(args.analyzer_command)
    abs_file_path = get_file_path(args.analyzer_command)
    preproc_name = get_preprocessed_repro_file(abs_file_path,
                                               args.analyzer_command)
    reduce(preproc_name, assert_string, args.analyzer_command, args.j)


if __name__ == '__main__':
    main()
