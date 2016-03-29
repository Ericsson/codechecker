#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

'''
CodeChecker test script
'''
import argparse
import base64
from functools import partial
import json
import logging
import multiprocessing
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

from test_helper import get_free_port

LOG = logging.getLogger('Package Tester')

msg_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
log_handler = logging.StreamHandler()
log_handler.setFormatter(msg_formatter)
LOG.setLevel(logging.INFO)
LOG.addHandler(log_handler)


def start_test_client(pkg_root, test_modules, e, err, fail, skipp, viewer_port, server_port, test_module_error):

    # set viewer env to find python modules

    with open(os.path.join(pkg_root, 'config', 'package_layout.json')) as layout_file:
        package_layout = json.load(layout_file)

    viewer_modules = \
        os.path.join(pkg_root, package_layout['static']['codechecker_gen'])

    sys.path.append(viewer_modules)
    sys.path.append(test_modules)

    # pass viewer port to clients
    os.environ['CC_TEST_VIEWER_PORT'] = str(viewer_port)
    os.environ['CC_TEST_SERVER_PORT'] = str(server_port)

    standard_tests = unittest.TestSuite()

    def load_tests(loader, standard_tests, s_dir):
        # top level directory cached on loader instance
        package_tests = loader.discover(start_dir=s_dir, pattern='test*.py')
        standard_tests.addTests(package_tests)
        return standard_tests

    test_loader = unittest.TestLoader()

    try:
        test_suite = load_tests(test_loader, standard_tests, test_modules)

        results = unittest.TestResult()

        test_suite.run(results)

        if len(results.errors) > 0:
            for r, t in results.errors:
                err[r.id()] = t

        if len(results.failures) > 0:
            for f, t in results.failures:
                fail[f.id()] = t

        if len(results.skipped) > 0:
            for s, t in results.skipped:
                skipp[s.id()] = t

        # testing done
        e.set()

    except ImportError as ierr:
        LOG.error(str(ierr))
        LOG.error('Failed to load tests')
        e.set()
        test_module_error.set()
        return
        # sys.exit(1)

    # except Exception as ex:
    #     LOG.error(str(ex))
    #     e.set()


def start_test_server(e, server_cmd, checking_env):

    proc = subprocess.Popen(server_cmd, env=checking_env)

    # blocking terminate until event is set
    e.wait()

    if proc.poll() is None:
        # proc is still running
        # stopping it
        LOG.info('Server is still running, stopping it.')
        proc.terminate()

    LOG.info('server stopped')


# ---------------------------------------------------------
class GenericPackageTester(object):

    # ---------------------------------------------------------------------
    def __init__(self,
                 pkg_root,
                 database,
                 test_proj_path,
                 test_project_config,
                 test_modules,
                 clang_version,
                 log,
                 cmd_args):

        self.pkg_root = pkg_root
        self.log = log
        self.test_proj_path = test_proj_path
        self.database = database
        self.start_test_client = \
            partial(start_test_client, pkg_root, test_modules)
        self.use_postgresql = cmd_args.postgresql

        try:
            if test_project_config is None:
                with open(os.path.join(test_proj_path, 'project_info.json')) as inf_file:
                    self.project_info = json.load(inf_file)
            else:
                with open(test_project_config) as inf_file:
                    self.project_info = json.load(inf_file)

        except IOError as ioerr:
            LOG.error('Failed to open config for testing.')
            LOG.error(ioerr)
            sys.exit(1)
        except ValueError as vaerr:
            LOG.error('Config format error.')
            LOG.error(vaerr)
            sys.exit(1)

        os.environ['CC_TEST_PROJECT_INFO'] = \
            json.dumps(self.project_info['clang_' + clang_version])
        self.workspace = tempfile.mkdtemp()
        self.log.info('Creating temporary directory: ' + self.workspace)
        self.env = self._get_check_env()

    def __del__(self):
        if hasattr(self, 'workspace') and os.path.exists(self.workspace):
            self.log.info('Removing temporary directory: ' + self.workspace)
            shutil.rmtree(self.workspace)

    def _get_check_env(self, env=os.environ):
        '''source the package to get the environment used to run the checker'''

        command = ['bash', '-c', '%s -c "import base64,os,pickle,sys;'
                                 'sys.stdout.write(base64.b64encode('
                                 'pickle.dumps(os.environ.copy(),protocol=2)).'
                                 'decode(\'ascii\'))"' %
                                 (sys.executable)]
        try:
            env['PATH'] = os.path.join(self.pkg_root, 'bin') + ':' + env['PATH']
            penv = subprocess.check_output(command, env=env)
        except subprocess.CalledProcessError as perr:
            self.log.error('Failed source codechecker package for testing')
            self.log.error(str(perr))
            # self.log.error('Failed to run command: ' + ' '.join(command))
            sys.exit(1)

        return pickle.loads(base64.b64decode(penv))

    # ---------------------------------------------------------------------
    def _clean_test_project(self, project_path, clean_cmd):
        self.log.debug('cleaning test project ' + project_path)

        command = ['bash', '-c', clean_cmd]

        try:
            subprocess.check_call(command, cwd=project_path, env=self.env)
        except subprocess.CalledProcessError as perr:
            self.log.error(str(perr))
            self.log.error('Test project cleaning failed, check the config')
            sys.exit(1)

    def _generate_suppress_file(self, suppress_file):
        """
        create a dummy supppress file just to check if the old and the new
        suppress format can be processed
        """
        import calendar
        import time
        import hashlib
        import random

        hash_version = '1'
        suppress_stuff = []
        for i in range(10):
            # epoch time
            t = calendar.timegm(time.gmtime())
            # random number
            r = random.randint(1, 9999999)
            n = str(t) + str(r)
            suppress_stuff.append(hashlib.md5(n).hexdigest() + '#' + hash_version)

        s_file = open(suppress_file, 'w')
        for k in suppress_stuff:
            s_file.write(k + '||' + 'idziei éléáálk ~!@#$#%^&*() \n')
            s_file.write(k + '||' + 'test_~!@#$%^&*.cpp' + '||' 'idziei éléáálk ~!@#$%^&*(\n')
            s_file.write(hashlib.md5(n).hexdigest() + '||' + 'test_~!@#$%^&*.cpp' + '||' 'idziei éléáálk ~!@#$%^&*(\n')

        s_file.close()

    def _generate_skip_list_file(self, skip_list_file):
        """
        create a dummy skip list file just to check if it can be loaded
        skip files without any results from checking
        """
        skip_list_content = []
        skip_list_content.append("-*randtable.c")
        skip_list_content.append("-*blocksort.c")
        skip_list_content.append("-*huffman.c")
        skip_list_content.append("-*decompress.c")
        skip_list_content.append("-*crctable.c")

        s_file = open(skip_list_file, 'w')
        for k in skip_list_content:
            s_file.write(k+'\n')

        s_file.close()

    # ---------------------------------------------------------------------
    def run_test(self):

        db = self.database

        test_config = {}
        test_config['CC_TEST_SERVER_PORT'] = get_free_port()
        test_config['CC_TEST_SERVER_HOST'] = 'localhost'
        test_config['CC_TEST_VIEWER_PORT'] = get_free_port()
        test_config['CC_TEST_VIEWER_HOST'] = 'localhost'

        test_project_path = self.test_proj_path
        test_project_clean_cmd = self.project_info['clean_cmd']
        test_project_build_cmd = self.project_info['build_cmd']

        codechecker_workspace = self.workspace
        #self.env['CODECHECKER_VERBOSE'] = 'debug'
        # self.env['CODECHECKER_ALCHEMY_LOG'] = '2'

        def run_check(suppress_file, skip_list_file):

            check_cmd = []
            check_cmd.append('CodeChecker')
            check_cmd.append('check')
            if self.use_postgresql:
                check_cmd.append('--postgresql')
                check_cmd.append('--dbaddress')
                check_cmd.append(db['dbaddress'])
                check_cmd.append('--dbport')
                check_cmd.append(str(db['dbport']))
                check_cmd.append('--dbname')
                check_cmd.append(db['dbname'])
                check_cmd.append('--dbusername')
                check_cmd.append(db['dbusername'])
            check_cmd.append('-w')
            check_cmd.append(codechecker_workspace)
            check_cmd.append('--suppress')
            check_cmd.append(suppress_file)
            check_cmd.append('--skip')
            check_cmd.append(skip_list_file)
            unique_id = uuid.uuid4().hex
            check_cmd.append('-n')
            check_cmd.append(self.project_info['name'] + '_' + unique_id)
            check_cmd.append('-b')
            check_cmd.append(test_project_build_cmd)
            check_cmd.append('--analyzers')
            check_cmd.append('clangsa')

            self.log.info(' '.join(check_cmd))

            try:
                subprocess.check_call(check_cmd, cwd=test_project_path,
                                      env=self.env)
                self.log.info('Checking the test project is done.')
            except subprocess.CalledProcessError as perr:
                self.log.error(str(perr))
                self.log.error('Failed to run command: ' + ' '.join(check_cmd))
                raise perr

        def start_server():
            server_cmd = []
            server_cmd.append('CodeChecker')
            server_cmd.append('server')
            server_cmd.append('--check-port')
            server_cmd.append(str(test_config['CC_TEST_SERVER_PORT']))
            if self.use_postgresql:
                server_cmd.append('--postgresql')
                server_cmd.append('--dbaddress')
                server_cmd.append(db['dbaddress'])
                server_cmd.append('--dbport')
                server_cmd.append(str(db['dbport']))
                server_cmd.append('--dbname')
                server_cmd.append(db['dbname'])
                server_cmd.append('--dbusername')
                server_cmd.append(db['dbusername'])
            server_cmd.append('--view-port')
            server_cmd.append(str(test_config['CC_TEST_VIEWER_PORT']))
            server_cmd.append('-w')
            server_cmd.append(codechecker_workspace)
            server_cmd.append('--suppress')
            server_cmd.append(suppress_file)

            self.log.info('Starting server.')
            self.log.info(' '.join(server_cmd))

            w2 = multiprocessing.Process(name='server',
                                         target=start_test_server,
                                         args=(stop_server, server_cmd, self.env))
            w2.start()

            # wait for server to start and connect to database
            time.sleep(15)

            manager = multiprocessing.Manager()

            err = manager.dict()
            fail = manager.dict()
            skipp = manager.dict()

            self.log.info('STARTING CLIENT TESTS...')
            w1 = multiprocessing.Process(
                name='test_client',
                target=self.start_test_client,
                args=(stop_server, err, fail, skipp,
                      test_config['CC_TEST_VIEWER_PORT'],
                      test_config['CC_TEST_SERVER_PORT'],
                      test_module_error))
            w1.start()
            # wait for test to finish
            w1.join()

            return err, fail, skipp

        self.log.info('Cleaning checker workspace')

        # generate suppress file
        suppress_file_fd, suppress_file = tempfile.mkstemp()
        self._generate_suppress_file(suppress_file)

        skip_list_file_fd, skip_list_file = tempfile.mkstemp()
        self._generate_skip_list_file(skip_list_file)

        # end ------------------

        self.log.info('Cleaning test project')
        # fist check
        self._clean_test_project(test_project_path, test_project_clean_cmd)
        run_check(suppress_file, skip_list_file)
        time.sleep(5)
        stop_server = multiprocessing.Event()
        test_module_error = multiprocessing.Event()

        # second check
        self._clean_test_project(test_project_path, test_project_clean_cmd)
        run_check(suppress_file, skip_list_file)

        time.sleep(5)
        stop_server = multiprocessing.Event()

        err, fail, skipp = start_server()
        # delete suppress file
        os.close(suppress_file_fd)
        os.remove(suppress_file)
        if test_module_error.is_set():
            LOG.error('Test module error')
            sys.exit(1)

        self.log.info('CLIENT TESTS DONE.')
        self.log.info('=====================================')
        self.log.info('TEST RESULTS:')
        self.log.info('=====================================')

        self.log.info('=====================================')
        self.log.info('TestCase errors: ' + str(len(err)))
        if err:
            self.log.info('=====================================')
            for id, msg in err.items():
                LOG.info(id)
                LOG.info(msg)

        self.log.info('=====================================')
        self.log.info('Failed TestCases: ' + str(len(fail)))
        if fail:
            self.log.info('=====================================')
            for id, msg in fail.items():
                LOG.info(id)
                LOG.info(msg)

        self.log.info('=====================================')
        self.log.info('Skipped TestCases: ' + str(len(skipp)))
        if skipp:
            self.log.info('=====================================')
            for id, msg in skipp.items():
                LOG.info(id)
                LOG.info(msg)

        self.log.info('=====================================')
        if fail or err:
            LOG.error('Some tests have failed!')
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='CodeChecker tester script',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--package', required=True, action='store',
                        dest='pkg_root', help='Path of the package to test.')
    parser.add_argument('-v', '--clang_version', default='stable',
                        action='store', choices={'stable', 'trunk'},
                        dest='clang_version', help='Version of the used clang.')
    parser.add_argument('-t', '--test_modules', default='tests/functional/regression_test',
                        action='store', dest='test_modules',
                        help='The directory containing the test files.')
    parser.add_argument('--project', default='tests/functional/src/bzip2',
                        action='store', dest='test_project',
                        help='Project to run the test checks on.')
    parser.add_argument('--project-config',
                        action='store', dest='test_project_config',
                        help='Test project config. By default tries to use from the test_project.')

    parser.add_argument('--postgresql', dest="postgresql",
                        action='store_true', default=False,
                        help='Use PostgreSQL database.')
    parser.add_argument('--dbaddress', type=str, dest="dbaddress",
                        default='localhost',
                        help='Postgres database server address.')
    parser.add_argument('--dbport', type=int, dest="dbport",
                        default=get_free_port(),
                        help='Postgres database server port.')
    parser.add_argument('--dbname', type=str, dest="dbname", default='testDb',
                        help='Name of the database.')
    parser.add_argument('--dbusername', type=str, dest="dbusername",
                        default='testUser', help='Database user name.')

    args = parser.parse_args()
    args.pkg_root = os.path.realpath(args.pkg_root)
    args.test_modules = os.path.realpath(args.test_modules)
    args.test_project = os.path.realpath(args.test_project)

    database = {k: vars(args)[k] for k in ('dbaddress', 'dbport', 'dbname',
                                           'dbusername')}

    LOG.info('Initializing new package tester')
    package_tester = GenericPackageTester(args.pkg_root,
                                          database,
                                          args.test_project,
                                          args.test_project_config,
                                          args.test_modules,
                                          args.clang_version,
                                          LOG,
                                          args)
    LOG.info('Running tests')
    package_tester.run_test()

if __name__ == '__main__':
    main()
