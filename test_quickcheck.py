#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

'''
Exectutes "quickcheck" related tests.
'''

import argparse
import base64
import logging
import os
import pickle
import subprocess
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'tests'))
from test_helper.testlog import LOG
from quickcheck_test.test import QuickCheckTest

class QuickCheckTester(object):
    '''Tester helper class.'''

    def _get_check_env(self):
        '''source the package to get the environment used to run the checker'''

        env = os.environ
        init_file = os.path.join(self.pkg_root, 'init', 'init.sh')

        command = ['bash', '-c', 'source %s > /dev/null && '
                                 '%s -c "import base64,os,pickle,sys;'
                                 'sys.stdout.write(base64.b64encode('
                                 'pickle.dumps(os.environ.copy(),protocol=2)).'
                                 'decode(\'ascii\'))"' % \
                                 (init_file, sys.executable)]
        try:
            penv = subprocess.check_output(command, env=env)
        except subprocess.CalledProcessError as perr:
            self.log.error('Failed source codechecker package for testing')
            self.log.error(str(perr))
            sys.exit(1)

        return pickle.loads(base64.b64decode(penv))

    def __init__(self, args):
        self.log = LOG
        self.log.setLevel(logging.INFO)
        self.pkg_root = args.pkg_root
        self.test_directory = args.test_directory

    def run(self):
        '''Entry point'''

        env = self._get_check_env()
        test = QuickCheckTest(self.test_directory, env, self.log)
        test.run_tests()

def main():
    '''Entry point'''

    parser = argparse.ArgumentParser(
        description='CodeChecker tester script',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--package', required=True, action='store',
                        dest='pkg_root', help='Path of the package to test.')
    parser.add_argument('-t', '--test_directory',
                        default='tests/quickcheck_test',
                        action='store', dest='test_directory',
                        help='The directory containing the test files.')

    args = parser.parse_args()
    args.pkg_root = os.path.realpath(args.pkg_root)
    args.test_directory = os.path.realpath(args.test_directory)

    tester = QuickCheckTester(args)
    tester.run()

if __name__ == '__main__':
    main()
