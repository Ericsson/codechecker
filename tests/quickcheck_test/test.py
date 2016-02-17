# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

'''
Test the "quickcheck" feature.

"quickcheck" tests are very simple: the main idea is to execte CodeChecker with
a set of "quickcheck" options then compare its output against the excepted
output. This is implemented using ".output" files.

The ".output" file format:
    The first line contains the command line options for "quickcheck". The
    second line is a comment. The rest of the file is the excepted output of the
    "quickcheck" command.
'''

import glob
import os
import sys
import subprocess

def _read_output_file(path):
    '''
    Reads the given output file and returns a pair of arguments and output
    lines as a single string.
    '''

    with open(path, 'r') as ofile:
        lines = ofile.readlines()
        return (lines[0].strip(), ''.join(lines[2:]))

class QuickCheckTest(object):
    '''Helper class for executing "quickcheck" test.'''

    def _run_tests_by_output_file(self, path):
        '''
        Exectures CodeChecker and checks its output by the given ".output" file.
        '''

        filename = os.path.basename(path)
        options, correct_output = _read_output_file(path)
        command = 'CodeChecker quickcheck --analyzers clangsa ' + options

        self.log.info("Executing %s test" % filename)
        output = subprocess.check_output(['bash', '-c', command],
                                         stderr=subprocess.STDOUT,
                                         env=self.env,
                                         cwd=self.test_dir)
        if output != correct_output:
            self.log.info('%s test failed!' % filename)
            self.log.error('COMMAND: %s' % command)
            self.log.error('OUTPUT:\n------\n%s\n------' % output)
            self.log.error('CORRECT OUTPUT:\n------\n%s\n------' % \
                correct_output)
            return False
        else:
            self.log.info('%s test OK!' % filename)
            return True

    def run_tests(self):
        '''Iterates over the test directory and runs all tests in it.'''

        failed = False
        for ofile in glob.glob(self.test_dir + os.sep + '*.output'):
            if not self._run_tests_by_output_file(ofile):
                failed = True

        if failed:
            self.log.error("Some tests have failed!")
            sys.exit(1)
        else:
            self.log.info("All tests have passed! :-)")

    def __init__(self, test_dir, env, log):
        self.test_dir = test_dir
        self.env = env
        self.log = log
