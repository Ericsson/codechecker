#!/usr/bin/env python2

import os
import logging
import subprocess
import zipfile
import argparse

LOGGER = logging.getLogger('ANALYZE HANDLER')
LOGGER.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)


def preAnalyze(analyze_id):
    LOGGER.info('Pre Analyze Step')

    zip_file_path = os.path.join(analyze_id, 'source.zip')

    with zipfile.ZipFile(zip_file_path) as zf:
        try:
            zf.extractall(analyze_id)
        except Exception:
            LOGGER.error("Failed to extract all files from the ZIP.")

    command_file_path = os.path.join(analyze_id, 'build_command')

    with open(command_file_path) as build_action:
        try:
            build_command = build_action.readlines()
        except Exception:
            LOGGER.error("Failed to read in build command.")

    file_name = build_command.rsplit(' ', 1)[1]

    run_command = build_command.rsplit(' ', 1)[0]

    for root, dirs, files in os.walk(path):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o744)
        for f in files:
            os.chmod(os.path.join(root, f), 0o744)
            if f == file_name:
                file_path = os.path.join(root, f)

    command = ["CodeChecker check"]
    command.append("-b")
    command.append("%s %s" % (run_command, file_path))
    command.append("-o")
    command.append("%s" % os.path.join(random_uuid, 'output'))

    LOGGER.info("Command        : %s" % command)

    process = subprocess.Popen(command,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    stdout, stderr = process.communicate()
    returncode = process.wait()

    LOGGER.info("Command output  : \n%s" % stdout)

    with open("stdout", "w") as text_file:
        text_file.write(stdout)

    LOGGER.debug("Error output   : %s" % stderr)

    with open("stderr", "w") as text_file:
        text_file.write(stderr)

    LOGGER.debug("Return code    : %s" % returncode)

    with open("returncode", "w") as text_file:
        text_file.write(returncode)


def postAnalyze(analyze_id):
    LOGGER.info('Post Analyze Step')

    with zipfile.ZipFile(random_uuid + '_output.zip', 'w') as output:
        for root, dirs, files in os.walk(os.path.join(random_uuid, 'output')):
            for f in files:
                output.write(os.path.join(root, f))


def main():
    parser = argparse.ArgumentParser(description=".....")

    parser.add_argument('-id', '--id', type=str, dest='id', help="...")

    args = parser.parse_args()


if __name__ == "__main__":
    main()
