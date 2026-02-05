#!/usr/bin/env python3

# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import argparse
import dataclasses
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


def print_dict(d: dict):
    max_key_length = max(map(len, d.keys()))
    for k, v in d.items():
        print(f"{k + ':':<{max_key_length + 2}}{v}")


def parse_date(date: str) -> datetime:
    return datetime.strptime(date, "%Y-%m-%d %H:%M:%S")


def date_diff(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds()


@dataclass
class DataStats:
    min: float = 0
    max: float = 0
    avg: float = 0


class EventType(Enum):
    WAIT_START = 1
    PROCESS_START = 2
    COMPLETED = 3


@dataclass
class TaskEvent:
    date: datetime
    type: EventType
    duration: float = 0


@dataclass
class DataPoint:
    date: datetime
    waiting_count: int = 0
    processing_count: int = 0
    completed_count: int = 0
    waiting_stats: Optional[DataStats] = None
    processing_stats: Optional[DataStats] = None


def calc_stats(float_list: list[float]) -> DataStats:
    return DataStats(
            min=min(float_list),
            max=max(float_list),
            avg=round(sum(float_list) / len(float_list), 2))


@dataclass
class ProcessingResult:
    total_status_count: dict = field(default_factory=dict)
    total_waiting_stats: Optional[DataStats] = None
    total_processing_stats: Optional[DataStats] = None
    intervals: list[DataPoint] = field(default_factory=list)


def check(data):
    print("Checking JSON file ...")

    if not isinstance(data, list):
        print("Error: Invalid JSON file!")

    if len(data) == 0:
        sys.exit("Error: No task data is available!")

    required_fields = ["status", "enqueuedAt", "startedAt", "completedAt"]

    for e in data:
        for r in required_fields:
            if r not in e:
                print("Error: Invalid JSON file!")
                print(f"Field '{r}' is missing in item {e}")
                sys.exit(1)

    print("JSON file is valid.")


def process(data, interval_duration: int) -> ProcessingResult:
    check(data)

    # Convert date strings to datetime objects.
    for e in data:
        for k in ["enqueuedAt", "startedAt", "completedAt"]:
            e[k] = parse_date(e[k]) if e[k] else None

    events: list[TaskEvent] = []
    total_waiting_durations: list[float] = []
    total_process_durations: list[float] = []
    status_count: dict[str, int] = {}

    for e in data:
        status: str = e["status"]
        enqueued_at: datetime = e["enqueuedAt"]
        started_at: datetime = e["startedAt"]
        completed_at: datetime = e["completedAt"]

        if status not in status_count:
            status_count[status] = 1
        else:
            status_count[status] += 1

        if status == "COMPLETED":
            waiting_dur: float = date_diff(enqueued_at, started_at)
            processing_dur: float = date_diff(started_at, completed_at)

            total_waiting_durations.append(waiting_dur)
            total_process_durations.append(processing_dur)

            events.append(TaskEvent(date=enqueued_at,
                                    type=EventType.WAIT_START,
                                    duration=waiting_dur))

            events.append(TaskEvent(date=started_at,
                                    type=EventType.PROCESS_START,
                                    duration=processing_dur))

            events.append(TaskEvent(date=completed_at,
                                    type=EventType.COMPLETED))

    events.sort(key=lambda e: e.date)

    intervals: list[DataPoint] = [DataPoint(date=events[0].date)]
    counter_waiting: int = 0
    counter_processing: int = 0
    waiting_durations: list[float] = []
    processing_durations: list[float] = []
    last: DataPoint = intervals[-1]

    for e in events:
        if (interval_duration != 0 and
                date_diff(last.date, e.date) > interval_duration):

            # Closing last interval
            last.waiting_count = counter_waiting
            last.processing_count = counter_processing
            last.waiting_stats = calc_stats(waiting_durations) \
                if waiting_durations else None
            last.processing_stats = calc_stats(processing_durations) \
                if processing_durations else None
            waiting_durations = []
            processing_durations = []

            # Create new interval
            intervals.append(DataPoint(date=e.date))
            last = intervals[-1]

        if e.type == EventType.WAIT_START:
            counter_waiting += 1
            waiting_durations.append(e.duration)
        elif e.type == EventType.PROCESS_START:
            counter_waiting -= 1
            counter_processing += 1
            processing_durations.append(e.duration)
        elif e.type == EventType.COMPLETED:
            counter_processing -= 1

    return ProcessingResult(
        total_status_count=status_count,
        total_waiting_stats=calc_stats(total_waiting_durations)
        if total_waiting_durations else None,
        total_processing_stats=calc_stats(total_process_durations)
        if total_process_durations else None,
        intervals=intervals)


def present(result: ProcessingResult,
            plot: bool, plot_sum: str,
            plot_engine: str):
    print("--- Total Status Count ---")
    print_dict(result.total_status_count)
    print("--- Total Waiting in Queue Time Statistics ---")
    print_dict({k: str(v) + " secs"
               for k, v in vars(result.total_waiting_stats).items()})
    print("--- Total Processing Time Statistics ---")
    print_dict({k: str(v) + " secs"
               for k, v in vars(result.total_processing_stats).items()})

    if plot:
        import matplotlib
        import matplotlib.pyplot as plt

        matplotlib.use(plot_engine)

        iv = result.intervals
        fig, axs = plt.subplots(2, 2)
        fig.suptitle("Serverside Task Statistics")

        x = [i.date for i in iv]
        y = [i.waiting_count for i in iv]
        axs[0, 0].step(x, y, 'y')
        axs[0, 0].set_ylabel("Number of tasks waiting in queue")

        x = [i.date for i in iv]
        y = [i.processing_count for i in iv]
        axs[1, 0].step(x, y)
        axs[1, 0].set_ylabel("Number of tasks being processed")

        iv_wait = list(filter(lambda e: e.waiting_stats, iv))
        x = [i.date for i in iv_wait]
        y = [getattr(i.waiting_stats, plot_sum) for i in iv_wait]
        axs[0, 1].step(x, y, 'y')
        axs[0, 1].set_ylabel(
            f"{plot_sum.upper()} waiting in queue time (secs)")

        iv_process = list(filter(lambda e: e.processing_stats, iv))
        x = [i.date for i in iv_process]
        y = [getattr(i.processing_stats, plot_sum) for i in iv_process]
        axs[1, 1].step(x, y)
        axs[1, 1].set_ylabel(
            f"{plot_sum.upper()} task processing time (secs)")

        try:
            plt.show()
        except KeyboardInterrupt:
            pass


def get_plot_sum_choices():
    return list(map(lambda e: e.name, dataclasses.fields(DataStats)))


class CustomArgFormatter(argparse.RawTextHelpFormatter,
                         argparse.ArgumentDefaultsHelpFormatter):
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=CustomArgFormatter,
                                     description="""
This script can be used to display useful metrics about the server-side tasks.
The required input is a JSON file, which can be generated using the
\"CodeChecker cmd serverside-tasks\" command. Using the --plot option,
you can generate graphs showing various statistics. This requires matplotlib
to be installed.""")

    parser.add_argument("json_file", help="""
JSON file containg a list of serverside tasks.
This file can be acquired by running the command below:
CodeChecker cmd serverside-tasks --url <server_url> --enqueued-after <date1>
    --enqueued-before <date2> --output json > out.json""")

    parser.add_argument('-i', '--interval',
                        dest="interval_duration",
                        type=int,
                        required=False,
                        default=60,
                        help="""
Interval duration in seconds. Task events are grouped into intervals of this
duration to compute various metrics, calculated separately for each
interval.""")

    parser.add_argument('--plot',
                        dest="plot",
                        action="store_true",
                        required=False,
                        default=False,
                        help="""
Displays the statistics plot. This requires matplotlib to be installed.""")

    parser.add_argument('--plot-summary',
                        dest="plot_sum",
                        type=str,
                        required=False,
                        choices=get_plot_sum_choices(),
                        default="avg",
                        help="""
Specifies the statistics shown in the right-hand plots.""")

    parser.add_argument('--plot-engine',
                        dest="plot_engine",
                        type=str,
                        required=False,
                        default="Qt5Agg",
                        help="""
Defines which rendering engine matplotlib uses.""")

    args = parser.parse_args()
    with open(args.json_file, encoding="utf-8") as f:
        json_data = json.load(f)
        present(process(json_data, args.interval_duration),
                args.plot,
                args.plot_sum,
                args.plot_engine)
