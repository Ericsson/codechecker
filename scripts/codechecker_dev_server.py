#!/usr/bin/env python3
"""
This script intents to help with development of CodeChecker server.
By using this wrapper, modification of the source files will restart the server.
"""

from pathlib import Path
import threading
import subprocess
import time
import os
import sys

from subprocess import Popen

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class SourceFileModifiedEventHandler(FileSystemEventHandler):
    __proc = None

    def __init__(self, args = None) -> None:
        self.__args = args if args else ["--skip-db-cleanup"]
        self.__source_path = None
        self.__event = None
        self.__prev_event_time = time.time()
        self.start_codechecker()
        super().__init__()

    def on_any_event(self, event):
        is_py = Path(event.src_path).suffix == ".py"
        if (
            not event.is_directory
            and event.event_type in ["modified", "deleted"]
            and is_py
        ):
            self.__source_path = event.src_path
            self.__event = event.event_type

            if time.time() - self.__prev_event_time > 4:
                self.__prev_event_time = time.time()
                self.hotswap()
            #else:
            #    print(f"Skipping hotswap because of too close refresh interval: {time.time() - self.__prev_event_time} seconds")
        return super().on_any_event(event)

    def stop_codechecker(self):
        self.__proc = Popen(
            ["CodeChecker", "server", "--stop-all"], stdout=subprocess.PIPE
        )

    def start_codechecker(self):
        command = ["CodeChecker", "server"]
        command.extend(self.__args)

        print(f"Starting CodeChecker server with command: {command}")

        self.__proc = Popen(command, stdout=subprocess.PIPE)
        for out_line in iter(self.__proc.stdout.readline, b""):
            print(out_line.decode("utf-8"), end="")
            if "Server waiting for client requests" in str(out_line):
                # print("Server started")
                t = threading.Thread(target=self.print_stdout)
                t.start()
                break
        if self.__proc.poll():
            print("CodeChecker exited")

    def print_stdout(self):
        try:
            for out_line in iter(self.__proc.stdout.readline, b""):
                print(out_line.decode("utf-8"), end="")
        except:
            # Process might be already killed
            pass

    def hotswap(self):
        print()
        print( "========================================================================================")
        print(f"   Source file {self.__source_path} {self.__event}, restarting CodeChecker server")
        print( "========================================================================================")
        print()
        self.stop_codechecker()
        self.__proc.communicate()
        # while not self.__proc.poll():
        # print("Waiting for CodeChecker to stop")
        # time.sleep(1)
        self.start_codechecker()


def check_env():
    if not os.environ.get("CC_LIB_DIR"):
        print("CC_LIB_DIR environment variable is not configured")
        print(
            "Please run: export CC_LIB_DIR=CC_LIB_DIR=$PWD/build/CodeChecker/lib/python3/"
        )
        sys.exit(1)


def main():
    check_env()
    event_handler = SourceFileModifiedEventHandler(args=sys.argv[1:])
    path = "./web"
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
