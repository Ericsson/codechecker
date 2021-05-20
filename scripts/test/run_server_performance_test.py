# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Performance tester for the server.
"""


import argparse
import csv
import datetime
import logging
import math
import os
import random
import signal
import subprocess
import sys
import threading
import time
from collections import defaultdict


LOG = logging.getLogger(__name__)

handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s %(asctime)s] - %(message)s')
handler.setFormatter(formatter)

LOG.setLevel(logging.INFO)
LOG.addHandler(handler)


VERBOSE = False
FINISH = False
PROCESSES = []
MYPID = os.getpid()


def return_duration(func):
    """
    This decorator makes the applied function return its original return value
    and its run duration respectively in a tuple.
    """
    def func_wrapper(*args, **kwargs):
        before = datetime.datetime.now()
        ret = func(*args, **kwargs)
        after = datetime.datetime.now()
        return ret, (after - before).total_seconds()

    return func_wrapper


def print_process_output(message, stdout, stderr):
    global VERBOSE

    if not VERBOSE:
        return

    LOG.info(message)
    LOG.info('-' * 20 + 'stdout' + '-' * 20)
    print(stdout)
    LOG.info('-' * 20 + 'stderr' + '-' * 20)
    print(stderr)
    LOG.info('-' * (40 + len('stdout')))


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Performance tester for CodeChecker storage.',
        epilog='This test simulates some user actions which are performed on '
               'a CodeChecker server. The test instantiates the given number '
               'of users. These users perform a run storage, some queries and '
               'run deletion. The duration of all tasks is measured. These '
               'durations are written to the output file at the end of the '
               'test in CSV format. The tasks are performed for all report '
               'directories by all users.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('input',
                        type=str,
                        metavar='file/folder',
                        nargs='+',
                        default='~/.codechecker/reports',
                        help="The analysis result files and/or folders.")
    parser.add_argument('--url',
                        type=str,
                        metavar='PRODUCT_URL',
                        dest='product_url',
                        default='localhost:8001/Default',
                        required=False,
                        help="The URL of the product to store the results "
                             "for, in the format of host:port/ProductName.")
    parser.add_argument('-o', '--output',
                        type=str,
                        required=True,
                        help="Output file name for printing statistics.")
    parser.add_argument('-u', '--users',
                        type=int,
                        default=1,
                        help="Number of users")
    parser.add_argument('-t', '--timeout',
                        type=int,
                        default=-1,
                        help="Timout in seconds. The script stops when the "
                             "timeout expires. If a negative number is given "
                             "then the script runs until it's interrupted.")
    parser.add_argument('-r', '--rounds',
                        type=int,
                        default=-1,
                        help="The user(s) will accomplist their jobs this "
                             "many times.")
    parser.add_argument('-b', '--beta',
                        type=int,
                        default=10,
                        help="In the test users are waiting a random amount "
                             "of seconds. The random numbers have exponential "
                             "distribution of the beta parameter can be "
                             "provided here.")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Print the output of CodeChecker commands.")

    return parser.parse_args()


class StatManager:
    """
    This class stores the statistics of the single user events and prints them
    in CSV format. To produce a nice output the users should do the same tasks
    in the same order, e.g. they should all store, query and delete a run
    in this order. In the output table a row belongs to each user. The columns
    are the durations of the accomplished tasks.
    """

    def __init__(self):
        # In this dictionary user ID is mapped to a list of key-value
        # pairs: the key is a process name the value is its duration.
        self._stats = defaultdict(list)

    def add_duration(self, user_id, task_name, duration):
        """
        Add the duration of an event to the statistics.
        """
        self._stats[user_id].append((task_name, duration))

    def print_stats(self, file_name):
        if not self._stats:
            return

        with open(file_name, 'w', encoding="utf-8", errors="ignore") as f:
            writer = csv.writer(f)

            longest = []
            for _, durations in self._stats.items():
                if len(durations) > len(longest):
                    longest = durations

            header = ['User'] + [x[0] for x in longest]

            writer.writerow(header)

            for user_id, durations in self._stats.items():
                writer.writerow([user_id] + [x[1] for x in durations])


class UserSimulator:
    """
    This class simulates a user who performs actions one after the other. The
    durations of the single actions are stored in the statistics.
    """

    _counter = 0

    def __init__(self, stat, beta):
        UserSimulator._counter += 1
        self._id = UserSimulator._counter
        self._actions = list()
        self._stat = stat
        self._beta = beta

    def get_id(self):
        return self._id

    def add_action(self, name, func, args):
        """
        This function adds a user action to be played later.
        name -- The name of the action to identify it in the statistics output.
        func -- A function object on which @return_duration decorator is
                applied.
        args -- A tuple of function arguments to be passed to func.
        """
        self._actions.append((name, func, args))

    def play(self):
        global FINISH

        for name, func, args in self._actions:
            if FINISH:
                break

            self._user_random_sleep()
            ret, duration = func(*args)
            self._stat.add_duration(self._id, name, duration)

            # The exit code of some commands (e.g. CodeChecker cmd diff) can be
            # 2 if some reports were found. We consider this exit code normal.
            if ret != 0 and ret != 2:
                LOG.error("'%s' job has failed with '%d' error code!",
                          name, ret)

                # In case of error we send a signal to the main thread which
                # will be able to abort this program with an error code.
                global MYPID
                os.kill(MYPID, signal.SIGINT)

    def _user_random_sleep(self):
        sec = -self._beta * math.log(1.0 - random.random())
        LOG.info("User %d is sleeping %d seconds", self._id, sec)
        time.sleep(sec)


@return_duration
def store_report_dir(report_dir, run_name, server_url):
    LOG.info("Storage of %s is started (%s)", run_name, report_dir)

    store_process = subprocess.Popen([
        'CodeChecker', 'store',
        '--url', server_url,
        '--name', run_name,
        report_dir],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="ignore")

    global PROCESSES
    PROCESSES.append(store_process)

    print_process_output("Output of storage",
                         *store_process.communicate())

    if store_process.returncode == 0:
        LOG.info("Storage of %s is done.", run_name)
    else:
        LOG.error("Storage of %s failed!", run_name)

    return store_process.returncode


@return_duration
def local_compare(report_dir, run_name, server_url):
    LOG.info("Local compare of %s is started (%s)", run_name, report_dir)

    compare_process = subprocess.Popen([
        'CodeChecker', 'cmd', 'diff',
        '--url', server_url,
        '-b', run_name,
        '-n', report_dir,
        '--unresolved'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="ignore")

    global PROCESSES
    PROCESSES.append(compare_process)

    print_process_output("Output of local compare",
                         *compare_process.communicate())

    if compare_process.returncode in [0, 2]:
        LOG.info("Local compare of %s is done.", run_name)
    else:
        LOG.error("Local compare of %s failed.", run_name)

    return compare_process.returncode


@return_duration
def get_reports(run_name, server_url):
    LOG.info("Getting report list for %s is started", run_name)

    report_process = subprocess.Popen([
        'CodeChecker', 'cmd', 'results',
        '--url', server_url,
        run_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="ignore")

    global PROCESSES
    PROCESSES.append(report_process)

    print_process_output("Output of result list",
                         *report_process.communicate())

    if report_process.returncode == 0:
        LOG.info("Getting report list for %s is done.", run_name)
    else:
        LOG.error("Getting report list for %s failed.", run_name)

    return report_process.returncode


@return_duration
def delete_run(run_name, server_url):
    LOG.info("Deleting run %s is started", run_name)

    delete_process = subprocess.Popen([
        'CodeChecker', 'cmd', 'del',
        '--url', server_url,
        '-n', run_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="ignore")

    global PROCESSES
    PROCESSES.append(delete_process)

    print_process_output("Output of run deletion",
                         *delete_process.communicate())

    if delete_process.returncode == 0:
        LOG.info("Deleting run %s is done.", run_name)
    else:
        LOG.error("Deleting run %s failed!", run_name)

    return delete_process.returncode


@return_duration
def get_statistics(run_name, server_url):
    LOG.info("Get checker statistics %s is started", run_name)

    sum_process = subprocess.Popen([
        'CodeChecker', 'cmd', 'sum',
        '--url', server_url,
        '-n', run_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="ignore")

    global PROCESSES
    PROCESSES.append(sum_process)

    print_process_output("Output of checker statistics",
                         *sum_process.communicate())

    if sum_process.returncode == 0:
        LOG.info("Get checker statistics %s is done.", run_name)
    else:
        LOG.error("Get checker statistics %s failed!", run_name)

    return sum_process.returncode


def simulate_user(report_dirs, server_url, stat, beta, rounds):
    user = UserSimulator(stat, beta)
    run_name = 'performance_test_' + str(user.get_id())

    for report_dir in report_dirs:
        user.add_action(
            'Storage',
            store_report_dir,
            (report_dir, run_name, server_url))

        user.add_action(
            'Comparison',
            local_compare,
            (report_dir, run_name, server_url))

        user.add_action(
            'Reports',
            get_reports,
            (run_name, server_url))

    user.add_action(
        'Statistics',
        get_statistics,
        (run_name, server_url))

    user.add_action(
        'Delete',
        delete_run,
        (run_name, server_url))

    while rounds != 0 and not FINISH:
        rounds -= 1
        user.play()


def main():
    global VERBOSE

    args = parse_arguments()

    VERBOSE = args.verbose

    stat = StatManager()
    timer = None

    def finish_test(signum, frame):
        LOG.error('-----> Performance test stops. '
                  'Please wait for stopping all subprocesses. <-----')

        global FINISH
        FINISH = True

        global PROCESSES
        for proc in PROCESSES:
            try:
                proc.terminate()
            except OSError:
                pass

        stat.print_stats(args.output)
        LOG.error("Performance test has timed out or killed!")

        if timer:
            timer.cancel()

        sys.exit(128 + signum)

    signal.signal(signal.SIGINT, finish_test)

    threads = [threading.Thread(
        target=simulate_user,
        daemon=True,
        args=(args.input, args.product_url, stat, args.beta, args.rounds))
        for _ in range(args.users)]

    for t in threads:
        t.start()

    if args.timeout > 0:
        global MYPID
        timer = threading.Timer(args.timeout,
                                lambda: os.kill(MYPID, signal.SIGINT))
        timer.start()

    for t in threads:
        t.join()

    # If all the threads are successfully finished we can cancel the timer.
    if timer:
        timer.cancel()

    stat.print_stats(args.output)


if __name__ == '__main__':
    main()
