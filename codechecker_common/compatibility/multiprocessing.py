# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Multiprocessing compatibility module.
"""
import sys

# pylint: disable=no-name-in-module
# pylint: disable=unused-import
if sys.platform == "darwin" or sys.platform.startswith("win32"):
    from multiprocess import (  # type: ignore
        Pipe, Pool, Process,
        Queue,
        Value,
        cpu_count
    )
    from multiprocess.managers import SyncManager  # type: ignore
else:
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing
    from multiprocessing.managers import SyncManager as _SyncManager

    # Python 3.14 changed the default start method on Linux to forkserver.
    # CodeChecker workers depend on inheriting state such as SQLAlchemy
    # engines, configured logging, and compiler information. Use fork for
    # process helpers to preserve the previous behavior.
    fork_context = multiprocessing.get_context("fork")

    class Pool(ProcessPoolExecutor):
        def __init__(self, max_workers=None, mp_context=None,
                     initializer=None, initargs=(), **kwargs):
            super().__init__(
                max_workers,
                mp_context if mp_context is not None else fork_context,
                initializer, initargs, **kwargs)

    class SyncManager(_SyncManager):
        def __init__(self, address=None, authkey=None, serializer='pickle',
                     ctx=None, **kwargs):
            super().__init__(
                address, authkey, serializer,
                ctx if ctx is not None else fork_context, **kwargs)

    Pipe = fork_context.Pipe
    Process = fork_context.Process
    Queue = fork_context.Queue
    Value = fork_context.Value
    cpu_count = multiprocessing.cpu_count
