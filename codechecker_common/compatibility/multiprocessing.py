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
    from multiprocess.pool import Pool as MultiprocessPool
    from multiprocess import cpu_count

    # Shim class intended to provide API compatibility between the
    # pools from multiprocess and concurrent.futures.
    class Pool(MultiprocessPool):  # type: ignore
        def __init__(self, *args, max_workers=None, **kwargs):
            super().__init__(*args, processes=max_workers, **kwargs)

        def map(self, fn, *iterables, chunksize=1):
            return super().starmap(fn, zip(*iterables), chunksize)
else:
    from concurrent.futures import ProcessPoolExecutor as Pool  # type: ignore
    from multiprocessing import cpu_count
