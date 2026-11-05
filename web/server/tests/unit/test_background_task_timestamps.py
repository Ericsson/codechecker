# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Regression tests for https://github.com/Ericsson/codechecker/issues/5106 -
background task timestamps must be stored as naive UTC values.

The timestamp columns of 'BackgroundTask' are timezone-less 'DateTime'
columns. Assigning timezone-aware values made psycopg2 send them as
'timestamptz', which PostgreSQL converted to the wall time of the session
'TimeZone'. Reading them back as UTC then shifted the heartbeat by the
server's UTC offset, and 'CodeChecker store' failed with a false
'TaskTimeoutError'.
"""

import unittest
from datetime import datetime, timedelta, timezone

from codechecker_server.api.tasks import \
    _db_timestamp_to_posix_epoch, _posix_epoch_to_db_timestamp
from codechecker_server.database.config_db_model import BackgroundTask


class BackgroundTaskTimestampTest(unittest.TestCase):

    def _assert_naive_utc_now(self, value: datetime | None):
        self.assertIsNotNone(value)
        self.assertIsNone(value.tzinfo)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.assertLess(abs(now - value), timedelta(seconds=5))

    def test_task_transitions_store_naive_utc(self):
        task = BackgroundTask(token="t", kind="k", summary="s",
                              machine_id="m", user_name=None)
        self._assert_naive_utc_now(task.last_seen_at)

        task.set_enqueued()
        self._assert_naive_utc_now(task.enqueued_at)

        task.set_running()
        self._assert_naive_utc_now(task.started_at)

        task.heartbeat()
        self._assert_naive_utc_now(task.last_seen_at)

        task.set_finished()
        self._assert_naive_utc_now(task.finished_at)

    def test_abandoned_task_stores_naive_utc(self):
        task = BackgroundTask(token="t", kind="k", summary="s",
                              machine_id="m", user_name=None)
        task.set_abandoned()
        self._assert_naive_utc_now(task.finished_at)

    def test_epoch_db_timestamp_round_trip(self):
        epoch = 1791374400
        db_timestamp = _posix_epoch_to_db_timestamp(epoch)

        self.assertIsNone(db_timestamp.tzinfo)
        self.assertEqual(db_timestamp, datetime(2026, 10, 7, 12, 0, 0))
        self.assertEqual(_db_timestamp_to_posix_epoch(db_timestamp), epoch)
