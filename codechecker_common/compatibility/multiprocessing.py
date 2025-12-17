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
if sys.platform in ["darwin", "win32"]:
    from multiprocess import \
        Pipe, Pool as _Pool, Process, \
        Queue, \
        Value, \
        cpu_count
    from multiprocess.managers import SyncManager

    class Pool:
        """
        Compatibility wrapper for multiprocess.Pool that accepts max_workers
        parameter (like concurrent.futures.ProcessPoolExecutor) for consistency
        across platforms.
        """
        def __init__(self, max_workers=None, processes=None, initializer=None,
                     initargs=(), **kwargs):
            if processes is None and max_workers is not None:
                processes = max_workers
            kwargs.pop('max_workers', None)
            self._pool = _Pool(processes=processes, initializer=initializer,
                               initargs=initargs, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._pool.close()
            self._pool.join()
            return False

        def map(self, func, *iterables, **kwargs):
            """
            Map function over iterables using the pool.

            This method mimics ProcessPoolExecutor.map() behavior which accepts
            multiple iterables. When multiple iterables are provided, they are
            zipped together and starmap is used to unpack the tuples.

            Note: 'timeout' parameter is not supported by multiprocess.Pool
            and will be silently ignored if provided.
            """
            pool_kwargs = {k: v for k, v in kwargs.items() if k != 'timeout'}

            if len(iterables) == 1:
                return self._pool.map(func, iterables[0], **pool_kwargs)
            else:
                zipped = zip(*iterables)
                return self._pool.starmap(func, zipped, **pool_kwargs)

        def close(self):
            """Close the pool, preventing new tasks from being submitted."""
            self._pool.close()

        def join(self):
            """Wait for worker processes to exit."""
            self._pool.join()
else:
    from concurrent.futures import ProcessPoolExecutor as Pool
    from multiprocessing import \
        Pipe, \
        Process, \
        Queue, \
        Value, \
        cpu_count
    from multiprocessing.managers import SyncManager
