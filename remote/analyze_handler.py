#!/usr/bin/env python2

"""
Handler for managing CodeChecker analyze, including source extract,
output collecting and compresssion.
"""

import argparse
import hashlib
import json
import logging
import os
import sched
import subprocess
import sys
import time
import zipfile
from enum import Enum

import redis

LOG = logging.getLogger('ANALYZE HANDLER')
LOG.setLevel(logging.INFO)
CH = logging.StreamHandler()
CH.setLevel(logging.INFO)
FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
CH.setFormatter(FORMATTER)
LOG.addHandler(CH)


class AnalyzeStatus(Enum):
    """
    Enums to represents state of analysis.
    """

    ID_PROVIDED = 'ID_PROVIDED'
    QUEUED = 'QUEUED'
    ANALYZE_IN_PROGRESS = 'ANALYZE_IN_PROGRESS'
    ANALYZE_COMPLETED = 'ANALYZE_COMPLETED'
    PREANALYZE_FAILED = 'PREANALYZE_FAILED'
    ANALYZE_FAILED = 'ANALYZE_FAILED'
    POSTANALYZE_FAILED = 'POSTANALYZE_FAILED'


def pre_analyze(analyze_id, part_number, workspace, use_cache):
    """
    This method extract sources and return some necessary parameter.
    """

    LOG.info('Pre Analyze Step')

    file_path = os.path.join(workspace, analyze_id)

    source_file_without_extension = 'source_' + str(part_number)

    source_file_with_extension = source_file_without_extension + '.zip'

    zip_file_path = os.path.join(file_path, source_file_with_extension)

    analyze_dir_path = os.path.join(file_path, source_file_without_extension)

    with zipfile.ZipFile(zip_file_path) as zip_file:
        try:
            zip_file.extractall(analyze_dir_path)
        except Exception:
            LOG.error('Failed to extract all files from the ZIP.')

        if use_cache:
            list_of_other_files = ['sources-root/build_command',
                                   'sources-root/file_path',
                                   'sources-root/cached_files']

            difference = set(zip_file.namelist()).difference(
                list_of_other_files)

            if difference:
                LOG.debug('Store files in Redis: \n%s', difference)
                for file_name in zip_file.namelist():
                    if file_name not in list_of_other_files:
                        LOG.debug(os.path.join(analyze_dir_path, file_name))
                        with open(os.path.join(analyze_dir_path, file_name), 'rb') as file:
                            file_in_bytes = file.read()
                            readable_hash = hashlib.md5(
                                file_in_bytes).hexdigest()
                            try:
                                REDIS_DATABASE.set(
                                    readable_hash, file_in_bytes)
                                LOG.debug(REDIS_DATABASE.get(readable_hash))
                            except Exception:
                                LOG.error(
                                    'Failed to store file %s in Redis.', file_name)
                                sys.exit(1)

    sources_root_path = os.path.join(analyze_dir_path, 'sources-root')

    build_command_file_path = os.path.join(sources_root_path, 'build_command')

    with open(build_command_file_path) as build_action:
        try:
            build_command = build_action.readline()
        except Exception:
            REDIS_DATABASE.hset(analyze_id, 'state',
                                AnalyzeStatus.PREANALYZE_FAILED.name)
            LOG.error('Failed to read in build command.')
            sys.exit(1)

    file_to_analyze_path = os.path.join(sources_root_path, 'file_path')

    with open(file_to_analyze_path) as read_in_file:
        try:
            read_in_file_path = read_in_file.readline()
        except Exception:
            REDIS_DATABASE.hset(analyze_id, 'state',
                                AnalyzeStatus.PREANALYZE_FAILED.name)
            LOG.error('Failed to read in file path.')
            sys.exit(1)

    if use_cache:
        cached_files_path = os.path.join(
            sources_root_path, 'cached_files')

        with open(cached_files_path) as read_in_cached_files:
            try:
                cached_files = read_in_cached_files.readline()
            except Exception:
                REDIS_DATABASE.hset(analyze_id, 'state',
                                    AnalyzeStatus.PREANALYZE_FAILED.name)
                LOG.error('Failed to read in skipped file list.')
                sys.exit(1)

        cached_files = json.loads(cached_files)

        if cached_files:
            LOG.debug('Restore files from Redis: \n%s', cached_files.items())

            for file_hash in cached_files:
                new_file_path = os.path.join(
                    sources_root_path, cached_files[file_hash][1:])
                if not os.path.exists(os.path.dirname(new_file_path)):
                    try:
                        os.makedirs(os.path.dirname(new_file_path))
                    except OSError:
                        LOG.error('Failed to create directories.')
                        sys.exit(1)

                with open(new_file_path, 'wb+') as file_to_write_out:
                    file_to_write_out.write(REDIS_DATABASE.get(file_hash))

    return analyze_dir_path, build_command, read_in_file_path


def analyze(analyze_id, analyze_dir_path, build_command, read_in_file_path):
    """
    This method execute the analysation.
    """

    LOG.info('Analyze Step')

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

    LOG.info('CodeChecker command: %s', command)

    REDIS_DATABASE.hset(analyze_id, 'state',
                        AnalyzeStatus.ANALYZE_IN_PROGRESS.name)

    process = subprocess.Popen(command,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()
    returncode = process.wait()

    LOG.debug('Command output: \n%s', stdout)
    with open(os.path.join(analyze_dir_path, 'output', 'stdout'), "w") as text_file:
        text_file.write(stdout)

    if returncode != 0:
        REDIS_DATABASE.hset(analyze_id, 'state',
                            AnalyzeStatus.ANALYZE_FAILED.name)

        LOG.error('Error output: %s', stderr)

        with open(os.path.join(analyze_dir_path, 'output', 'stderr'), "w") as text_file:
            text_file.write(stderr)

        LOG.error('Return code: %s', returncode)

        with open(os.path.join(analyze_dir_path, 'output', 'returncode'), "w") as text_file:
            text_file.write(str(returncode))


def post_analyze(analyze_id, part_number, workspace):
    """
    This method collect outputs and compress those to a single zip file.
    """

    LOG.info('Post Analyze Step')

    file_path = os.path.join(workspace, analyze_id)

    source_file_without_extension = 'source_' + str(part_number)

    analyze_dir_path = os.path.join(file_path, source_file_without_extension)

    output_dir_path = os.path.join(analyze_dir_path, 'output')

    analyze_output_zip_file_path = os.path.join(file_path, 'output.zip')

    with zipfile.ZipFile(analyze_output_zip_file_path, 'a') as output:
        for root, dirs, files in os.walk(output_dir_path):
            for file in files:
                output.write(os.path.join(root, file))

    REDIS_DATABASE.hincrby(analyze_id, 'completed_parts', 1)

    parts = REDIS_DATABASE.hget(analyze_id, 'parts').decode('utf-8')
    completed_parts = REDIS_DATABASE.hget(analyze_id, 'completed_parts').decode('utf-8')

    if parts == completed_parts:
        REDIS_DATABASE.hset(analyze_id, 'state',
                            AnalyzeStatus.ANALYZE_COMPLETED.name)
        LOG.info('Analyze %s is completed.', analyze_id)


def main():
    parser = argparse.ArgumentParser(description=".....")

    parser.add_argument('-w', '--workspace', type=str, dest='workspace',
                        default='/workspace', help="...")

    parser.add_argument('--no-cache', dest='use_cache',
                        default=True, action='store_false')

    args = parser.parse_args()

    scheduler = sched.scheduler(time.time, time.sleep)

    def check_queue():
        scheduler.enter(10, 1, check_queue, ())
        LOG.info('Check task queue in Redis.')
        tasks = REDIS_DATABASE.lrange('ANALYSES_QUEUE', 0, -1)

        task = REDIS_DATABASE.lpop('ANALYSES_QUEUE')

        if task is not None:
            LOG.info(
                'Got a task: %s, starting analyze it, leftover task(s) %s', task, len(tasks))
            analyze_id, part_number = str(task.decode('utf-8')).split('-')

            try:
                analyze_dir_path, build_command, file_to_analyze_path = pre_analyze(
                    analyze_id, part_number, args.workspace, args.use_cache)
            except Exception:
                REDIS_DATABASE.hset(analyze_id, 'state',
                                    AnalyzeStatus.PREANALYZE_FAILED.name)
                LOG.error('Failed pre-analyze step to read in file path.')

            try:
                analyze(analyze_id, analyze_dir_path,
                        build_command, file_to_analyze_path)
            except Exception:
                REDIS_DATABASE.hset(analyze_id, 'state',
                                    AnalyzeStatus.ANALYZE_FAILED.name)
                LOG.error('Failed to read in file path.')

            try:
                post_analyze(analyze_id, part_number, args.workspace)
            except Exception:
                REDIS_DATABASE.hset(analyze_id, 'state',
                                    AnalyzeStatus.PREANALYZE_FAILED.name)
                LOG.error('Failed to read in file path.')

        else:
            LOG.info('No task.')

    def schedule():
        # check analyses queue in every 10 seconds
        scheduler.enter(10, 1, check_queue, ())
        scheduler.run()

    schedule()


if __name__ == "__main__":
    REDIS_DATABASE = redis.Redis(host='redis', port=6379, db=0)
    main()
