#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Measures store times of the specified Codechecker releases with the specified
results directory.
"""


import subprocess
import tempfile
import re
import time
from timeit import default_timer as timer

from pathlib import Path
from argparse import ArgumentParser

import random


def main(args):
    """
    Run Codechecker stores and measure elapsed times.
    """
    timesheet = {}

    random.seed()
    for binary in args.binaries:
        version_p = subprocess.run([binary, "version"], stdout=subprocess.PIPE)
        m = re.search(
            r"(Base package version\D*)(\d+.\d+.\d+)",
            version_p.stdout.decode("utf8")
        )
        version = m.group(2) if m.group(2) else binary

        timesheet[version] = []
        for count in range(args.count):
            with tempfile.TemporaryDirectory() as tmpdir:
                server = subprocess.Popen([binary, "server", "-w", tmpdir])
                time.sleep(3)  # wait for server spin up.
                store_time = timer()

                # sleep_time = random.random() # uncomment for testing
                # time.sleep(sleep_time) # comment subprocess&sleep calls
                subprocess.Popen(
                    [
                        binary,
                        "store",
                        "--name",
                        f"store_test_{count}",
                        args.reports
                    ]
                ).communicate()

                elapsed_store_time = timer() - store_time
                timesheet[version].append(elapsed_store_time)
                server.terminate()
                time.sleep(3)  # wait for server shutdown

    for _, v in timesheet.items():
        avg = sum(v) / len(v)
        v.append(avg)

    print_table(timesheet)


def print_table(measurements):
    for tool, times in measurements.items():
        print("| version: {} ".format(tool), end="")
        print(
            "| measurements (s): [{}] | avg. (s): {:.2f} |".format(
                ", ".join(["{:.2f}".format(x) for x in times[0:-1]]), times[-1]
            )
        )


if __name__ == "__main__":
    parser = ArgumentParser(
        description="""
                    Measures store times of the specified Codechecker
                    releases with the specified results directory.
                    """
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=3,
        help="""
            Replication count,
            how many times the store will run.
            """,
    )
    parser.add_argument(
        "-b",
        "--binaries",
        nargs="+",
        type=Path,
        required=True,
        help="""
            Pass the binaries here.
            """,
    )
    parser.add_argument(
        "-r",
        "--reports",
        type=Path,
        required=True,
        help="""
            Pass the reports directory here, that the analyze
            generated.
            """,
    )
    main(parser.parse_args())
