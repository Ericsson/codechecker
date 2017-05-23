# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import argparse
import csv
import datetime
import json
import logging
import multiprocessing
import ntpath
import os
import sys
import time
import zlib


from StringIO import StringIO
from multiprocessing import Process, Value, Lock, Manager
from uuid import uuid4

from shared.ttypes import BugPathPos
from shared.ttypes import BugPathEvent
from shared.ttypes import Severity
from libtest.thrift_client_to_db import CCReportHelper, CCViewerHelper
from libtest.thrift_client_to_db import get_all_run_results


logging.basicConfig(format='[%(process)s] %(message)s', level=logging.INFO)
log = logging.getLogger('PERF')


class Timer():
    """
    Simple timer context manager
    to measure code block execution time.
    """
    def __init__(self, measure_id, measure_data):
        self.measure_data = measure_data
        self.measure_id = measure_id
        self.before = None
        self.after = None

    def __enter__(self):
        self.before = datetime.datetime.now()

    def __exit__(self, type, value, traceback):
        after = datetime.datetime.now()
        self.measure_data[self.measure_id] = \
            (after - self.before).total_seconds()


def parse_arguments():
    """
    Parse arguments.
    """

    parser = argparse.ArgumentParser(
        description='Performance tester for CodeChecker package.')

    parser.add_argument('--output',
                        '-o',
                        dest='output',
                        default=os.path.join(os.path.dirname(__file__)),
                        help='Output directory for the results.')

    parser.add_argument('--test-config', required=True,
                        dest='test_config',
                        help='Test config in json format.')

    parser.add_argument('-j', type=int, default=1,
                        dest='job_num',
                        help='Number of jobs to start.')

    parser.add_argument('--keep', action='store_true',
                        dest='keep',
                        help='Keep the stored results in the database,'
                             ' do not delete them.')

    parser.add_argument('-v', action='store_true',
                        dest='verbose',
                        help='Enable verbose log.')

    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    return args


def get_test_host(test_conf):
    host = test_conf.get("host", "localhost")
    return host


def get_viewer_host_port(test_conf):
    """
    Get the viewer server related configuration from the
    test config.
    """
    view_host = get_test_host(test_conf)
    view_port = test_conf.get("view_port", "8001")

    return view_host, view_port


def get_check_server_host_port(test_conf):
    """
    Get the viewer server related configuration from the
    test config.
    """
    check_host = get_test_host(test_conf)
    check_port = test_conf.get("check_port", "9999")

    return check_host, check_port


def add_measurement_data(run_id, perf_data, measurement_result):
    """
    Update the collected measurement data.
    """

    data = perf_data.get(run_id)
    if data:
        data.update(measurement_result)
    else:
        data = measurement_result

    perf_data.update({run_id: data})


def delete_results(host, port, run_id, performance_data):
    """
    Remove run result for a run and measure remove time.
    """

    with CCViewerHelper(host, port, '/') as viewer_client:

        run_perf = {}
        with Timer('removeRunResults', run_perf):
            viewer_client.removeRunResults([run_id])
        add_measurement_data(run_id, performance_data, run_perf)


def store(test_conf, run_name, file_content):
    """
    Store a new analysis run with multiple reports.
    """

    check_host, check_port = get_check_server_host_port(test_conf)

    with CCReportHelper(check_host, check_port) as store_server:

        run_id = store_server.addCheckerRun('command',
                                            run_name,
                                            'version',
                                            False)

        store_reports(run_id, file_content, test_conf)

        store_server.finishCheckerRun(run_id)

    return run_id


def store_reports(run_id, file_content, test_conf):
    """
    Generate and store build actions, reports, file content.
    """

    number_of_files = test_conf.get("number_of_files", 1)
    bug_per_file = test_conf.get("bug_per_file", 1)
    bug_length = test_conf.get("bug_length", 1)

    check_host, check_port = get_check_server_host_port(test_conf)

    with CCReportHelper(check_host, check_port) as store_server:

        for file_count in range(number_of_files):

            ba_id = store_server.addBuildAction(run_id,
                                                'build_cmd_' +
                                                str(file_count),
                                                'check_cmd_' +
                                                str(file_count),
                                                "clangsa",
                                                'target_' +
                                                str(file_count)
                                                )

            file_id = store_server.needFileContent(run_id,
                                                   'file_' +
                                                   str(file_count)
                                                   ).fileId

            store_server.addFileContent(file_id, file_content)

            store_server.finishBuildAction(ba_id, '')
            for bug_count in range(bug_per_file):
                bug_paths = []
                bug_events = []
                for bug_element_count in range(bug_length):
                    line = bug_count * bug_length + bug_element_count + 1

                    bug_paths.append(BugPathPos(line,  # start line
                                                1,  # start col
                                                line,  # end line
                                                10,  # end col
                                                file_id)  # file id
                                     )

                    bug_events.append(BugPathEvent(line,  # start line
                                                   1,  # start col
                                                   line,  # end line
                                                   10,  # end col
                                                   'event_msg',  # checker msg
                                                   file_id)  # file id
                                      )

                bug_hash = 'hash_' + str(run_id) + '_' + str(file_count) + \
                    '_' + str(bug_count)

                r_id = store_server.addReport(ba_id,
                                              file_id,
                                              bug_hash,
                                              'checker_message',
                                              bug_paths,
                                              bug_events,
                                              'checker_name',
                                              'checker_cat',
                                              'bug_type',
                                              Severity.STYLE,
                                              False)


def measure(test_conf,
            performance_data,
            store_done,
            proc_done_counter,
            proc_counter_lock,
            keep):
    """
    Fill up a run with the configured values.
    """

    try:

        log.debug("Generating and storing results ...")

        number_of_runs = test_conf.get("number_of_runs", 1)

        # TODO: simulate append by using the same run name in multiple threads
        run_perf = {}
        for run_count in range(number_of_runs):
            run_name = 'name_' + str(run_count) + '_' + str(uuid4())
            file_line_size = test_conf.get("file_line_size")
            file_content = zlib.compress('\n'.join(['A' * 80] *
                                                   file_line_size),
                                         zlib.Z_BEST_COMPRESSION)

            with Timer('store', run_perf):
                run_id = store(test_conf, run_name, file_content)

            log.debug("Storing results for run " + str(run_id) + " done.")

            with proc_counter_lock:
                proc_done_counter.value -= 1

            # wait here for other processes to finish storing results
            # before measuiring queries
            store_done.wait()

            view_host, view_port = get_viewer_host_port(test_conf)

            with CCViewerHelper(view_host, view_port, '/') as viewer_client:

                with Timer('getRunData', run_perf):
                    run_data = viewer_client.getRunData()

                with Timer('getAllRunResulst', run_perf):
                    res = get_all_run_results(viewer_client, run_id)

                with Timer('getReportDetails', run_perf):
                    viewer_client.getReportDetails(res[-1].reportId)

                add_measurement_data(run_id, performance_data, run_perf)

                clean_after_fill = test_conf.get("clean_after_fill", True)
                if clean_after_fill and not keep:
                    delete_results(view_host,
                                   view_port,
                                   run_id,
                                   performance_data)

    except Exception as ex:
        log.error(ex)
        with proc_counter_lock:
            proc_done_counter.value -= 1
        sys.exit(1)


def process_perf_data(perf_data, output):
    """
    Process the collected performance data.
    """

    log.info("Processing resuls ...")
    buf = StringIO()
    writer = csv.writer(buf, dialect='excel')

    run_id, data = perf_data.items()[-1]
    top_row = ["run_id"]
    top_row.extend(list(sorted(data.keys())))

    writer.writerow(tuple(top_row))

    for perf_data in perf_data.items():
        run_id, data = perf_data
        data["run_id"] = run_id
        data_row = []
        for key in top_row:
            try:
                data_row.append(data[key])
            except Exception as ex:
                log.error(ex)

        writer.writerow(data_row)

    output.write(buf.getvalue())
    buf.close()
    log.info("Processing results done.")


def main():

    args = parse_arguments()

    manager = Manager()
    performance_data = manager.dict()

    with open(args.test_config) as test_config:
        test_conf = json.loads(test_config.read())

    _, file_name = ntpath.split(args.test_config)
    measure_id, _ = os.path.splitext(file_name)

    log.info("Starting performance tests for: " + measure_id)

    # block processes before measuring queries
    # wait for all processes to store generated results
    store_done = multiprocessing.Event()

    wait = test_conf.get("wait_for_store", False)
    if wait:
        store_done.set()

    proc_done_counter = Value('i', args.job_num)
    proc_counter_lock = Lock()

    procs = [Process(target=measure,
                     args=(test_conf,
                           performance_data,
                           store_done,
                           proc_done_counter,
                           proc_counter_lock,
                           args.keep))
             for i in range(args.job_num)]

    for proc in procs:
        proc.start()

    log.info("Measuring report storage time.")
    if wait:
        while proc_done_counter.value != 0:
            time.sleep(1)
            sys.stdout.write('.')
            sys.stdout.flush()

        sys.stdout.write('\n')

    log.info("Measuring queries ...")
    store_done.set()

    for proc in procs:
        proc.join()

    log.info("Measuring queries done.")

    if not test_conf.get("clean_after_fill", True) and not args.keep:

        view_host, view_port = get_viewer_host_port(test_conf)

        del_procs = [Process(target=delete_results,
                             args=(view_host,
                                   view_port,
                                   run_id,
                                   performance_data))
                     for run_id in performance_data.keys()]

        for proc in del_procs:
            proc.start()

        for proc in del_procs:
            proc.join()

    if not len(performance_data):
        log.info("There are no measurements results")
        sys.exit(0)

    file_name = measure_id + '.csv'

    if not os.path.exists(args.output):
        os.makedirs(args.output)
    output = os.path.join(args.output, file_name)
    with open(output, 'w+') as out:
        process_perf_data(performance_data, out)
    log.info('Measurement results:\n' + str(output))


if __name__ == '__main__':
    main()
