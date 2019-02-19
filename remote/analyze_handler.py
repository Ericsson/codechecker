#!/usr/bin/env python2

"""
Handler for managing CodeChecker analyze, including source extract,
output collecting and compresssion.
"""

import os
import logging
import subprocess
import zipfile
import redis
import sched
import time
import argparse

from enum import Enum

LOGGER = logging.getLogger('ANALYZE HANDLER')
LOGGER.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)


class AnalyzeStatus(Enum):
    ID_PROVIDED = 'ID_PROVIDED'
    QUEUED = 'QUEUED'
    ANALYZE_IN_PROGRESS = 'ANALYZE_IN_PROGRESS'
    ANALYZE_COMPLETED = 'ANALYZE_COMPLETED'
    PREANALYZE_FAILED = 'PREANALYZE_FAILED'
    ANALYZE_FAILED = 'ANALYZE_FAILED'
    POSTANALYZE_FAILED = 'POSTANALYZE_FAILED'


def preAnalyze(analyze_id, part_number, workspace):
    """
    This method extract sources and return some necessary parameter.
    """

    LOGGER.info('Pre Analyze Step')

    file_name = 'source'
    file_extension = '.zip'

    file_path = os.path.join(workspace, analyze_id)

    source_file_without_extension = file_name + '_' + str(part_number)
    source_file_with_extension = source_file_without_extension + file_extension

    zip_file_path = os.path.join(file_path, source_file_with_extension)

    analyze_dir_path = os.path.join(file_path, source_file_without_extension)

    with zipfile.ZipFile(zip_file_path) as zf:
        try:
            zf.extractall(analyze_dir_path)
        except Exception:
            LOGGER.error("Failed to extract all files from the ZIP.")

    command_file_path = os.path.join(
        analyze_dir_path, 'sources-root', 'build_command')

    with open(command_file_path) as build_action:
        try:
            build_command = build_action.readline()
        except Exception:
            REDIS_DATABASE.hset(analyze_id, 'state',
                                AnalyzeStatus.PREANALYZE_FAILED.name)
            LOGGER.error("Failed to read in build command.")

    file_to_analyze_path = os.path.join(
        analyze_dir_path, 'sources-root', 'file_path')

    with open(file_to_analyze_path) as read_in_file:
        try:
            read_in_file_path = read_in_file.readline()
        except Exception:
            REDIS_DATABASE.hset(analyze_id, 'state',
                                AnalyzeStatus.PREANALYZE_FAILED.name)
            LOGGER.error("Failed to read in file path.")

    return analyze_dir_path, build_command, read_in_file_path


def analyze(analyze_id, analyze_dir_path, build_command, read_in_file_path):
    """
    This method execute the analysation.
    """

    LOGGER.info('Analyze Step')

    build_command_for_codechecker = build_command.replace(
        read_in_file_path, analyze_dir_path + '/sources-root' + read_in_file_path)

    codechecker_path = os.path.join(
        os.getcwd(), "build/CodeChecker/bin/CodeChecker")

    command = []
    command.append("%s" % codechecker_path)
    command.append("check")
    command.append("-b")
    command.append("%s" % build_command_for_codechecker)
    command.append("-o")
    command.append("%s" % os.path.join(analyze_dir_path, 'output'))

    LOGGER.debug("CodeChecker command: %s" % command)

    REDIS_DATABASE.hset(analyze_id, 'state',
                        AnalyzeStatus.ANALYZE_IN_PROGRESS.name)

    process = subprocess.Popen(command,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()
    returncode = process.wait()

    LOGGER.debug("Command output: \n%s" % stdout)

    with open("stdout", "w") as text_file:
        text_file.write(stdout)

    if returncode != 0:
        REDIS_DATABASE.hset(analyze_id, 'state',
                            AnalyzeStatus.ANALYZE_FAILED.name)

        LOGGER.debug("Error output: %s" % stderr)

        with open("stderr", "w") as text_file:
            text_file.write(stderr)

        LOGGER.debug("Return code: %s" % returncode)

        with open("returncode", "w") as text_file:
            text_file.write(str(returncode))


def postAnalyze(analyze_id, part_number, workspace):
    """
    This method collect outputs and compress those to a single zip file.
    """

    LOGGER.info('Post Analyze Step')

    file_name = 'source'
    file_extension = '.zip'

    file_path = os.path.join(workspace, analyze_id)

    source_file_without_extension = file_name + '_' + str(part_number)

    analyze_dir_path = os.path.join(file_path, source_file_without_extension)

    output_dir_path = os.path.join(analyze_dir_path, 'output')

    analyze_output_zip_file_path = os.path.join(file_path, 'output.zip')

    with zipfile.ZipFile(analyze_output_zip_file_path, 'a') as output:
        for root, dirs, files in os.walk(output_dir_path):
            for f in files:
                output.write(os.path.join(root, f))

    REDIS_DATABASE.hincrby(analyze_id, 'completed_parts', 1)

    parts = REDIS_DATABASE.hget(analyze_id, 'parts')
    completed_parts = REDIS_DATABASE.hget(analyze_id, 'completed_parts')

    if parts == completed_parts:
        REDIS_DATABASE.hset(analyze_id, 'state',
                            AnalyzeStatus.ANALYZE_COMPLETED.name)


def main():
    parser = argparse.ArgumentParser(description=".....")

    parser.add_argument('-w', '--workspace', type=str, dest='workspace',
                        default='/workspace', help="...")

    args = parser.parse_args()

    scheduler = sched.scheduler(time.time, time.sleep)

    def check_queue():
        scheduler.enter(10, 1, check_queue, ())
        LOGGER.info("Check task queue in Redis.")
        tasks = REDIS_DATABASE.lrange('ANALYSES_QUEUE', 0, -1)

        task = REDIS_DATABASE.lpop('ANALYSES_QUEUE')

        if task is not None:
            LOGGER.info(
                "Got a task: %s, starting analyze it, leftover tasks %s" % (task, len(tasks)))
            analyze_id, part_number = str(task).split('-')
            try:
                analyze_dir_path, build_command, file_to_analyze_path = preAnalyze(
                    analyze_id, part_number, args.workspace)
            except Exception:
                REDIS_DATABASE.hset(analyze_id, 'state',
                                    AnalyzeStatus.PREANALYZE_FAILED.name)
                LOGGER.error("Failed pre-analyze step to read in file path.")

            try:
                analyze(analyze_id, analyze_dir_path,
                        build_command, file_to_analyze_path)
            except Exception:
                REDIS_DATABASE.hset(analyze_id, 'state',
                                    AnalyzeStatus.ANALYZE_FAILED.name)
                LOGGER.error("Failed to read in file path.")

            try:
                postAnalyze(analyze_id, part_number, args.workspace)
            except Exception:
                REDIS_DATABASE.hset(analyze_id, 'state',
                                    AnalyzeStatus.PREANALYZE_FAILED.name)
                LOGGER.error("Failed to read in file path.")

        else:
            LOGGER.info("No task.")

    def schedule():
        # check analyses queue in every 10 seconds
        scheduler.enter(10, 1, check_queue, ())
        scheduler.run()

    schedule()


if __name__ == "__main__":
    REDIS_DATABASE = redis.Redis(
        host='redis', port=6379, db=0, charset="utf-8", decode_responses=True)
    main()
