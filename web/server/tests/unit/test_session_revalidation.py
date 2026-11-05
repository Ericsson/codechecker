# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Unit tests for cross-worker session invalidation (CWE-613).

A logout deletes the session record from the configuration database, but the
in-memory session caches are per-worker-process. These tests verify that a
cached session is re-validated against the database and dropped from the local
store once its token no longer exists there, that the validity check is
throttled by 'refresh_time', and that the throttle works independently of
which worker last refreshed the shared record.
"""

import unittest
from datetime import datetime, timedelta

from codechecker_server.session_manager import _Session


class _FakeQuery:
    """Minimal stand-in for a SQLAlchemy query chain."""

    def __init__(self, result):
        self._result = result

    def filter(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def one_or_none(self):
        return self._result


class _FakeTransaction:
    """Minimal stand-in for a SQLAlchemy session/transaction."""

    def __init__(self, result):
        self._result = result
        self.committed = False
        self.closed = False

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self._result)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class _FakeRecord:
    """Minimal stand-in for a SessionRecord row."""

    def __init__(self, last_access):
        self.last_access = last_access


def _make_db_factory(record):
    """Return a callable mimicking a DB session factory, counting how many
    times it was invoked (i.e. how many DB round-trips happened)."""
    transaction = _FakeTransaction(record)
    calls = {"count": 0}

    def factory():
        calls["count"] += 1
        return transaction

    factory.transaction = transaction
    factory.calls = calls
    return factory


def _make_session(database, refresh_time=60, session_lifetime=300,
                  last_access=None):
    return _Session(
        token="a" * 32,
        username="user",
        groups=[],
        session_lifetime=session_lifetime,
        refresh_time=refresh_time,
        is_root=False,
        database=database,
        last_access=last_access)


def _ago(seconds):
    return datetime.now() - timedelta(seconds=seconds)


class SessionRevalidationTest(unittest.TestCase):
    """Tests for _Session.revalidate() database validity checking."""

    def test_revalidate_true_when_record_exists(self):
        """Refresh window elapsed, token still in DB -> valid."""
        db = _make_db_factory(_FakeRecord(_ago(120)))
        sess = _make_session(db, last_access=_ago(120))
        self.assertTrue(sess.revalidate())
        self.assertEqual(db.calls["count"], 1)

    def test_revalidate_false_when_record_missing(self):
        """Refresh window elapsed, token deleted (logout on another worker)
        -> invalid."""
        db = _make_db_factory(None)
        sess = _make_session(db, last_access=_ago(120))
        self.assertFalse(sess.revalidate())
        self.assertEqual(db.calls["count"], 1)

    def test_revalidate_false_when_not_alive(self):
        """An expired (dead) session can never be revalidated."""
        db = _make_db_factory(_FakeRecord(_ago(120)))
        sess = _make_session(db, session_lifetime=0, last_access=_ago(120))
        self.assertFalse(sess.revalidate())


class RefreshThrottleTest(unittest.TestCase):
    """Tests for the refresh_time throttling of the database check."""

    def test_within_window_skips_db_check(self):
        """Inside the refresh window the cached session is trusted without a
        database round-trip -- even if the record has since been deleted."""
        db = _make_db_factory(None)  # record already gone
        sess = _make_session(db, refresh_time=60, last_access=datetime.now())
        self.assertTrue(sess.revalidate())
        self.assertEqual(db.calls["count"], 0)

    def test_window_elapsed_advances_local_timestamp_and_throttles(self):
        """Regression guard: after a successful check the worker's local
        last_access must advance even when another worker had refreshed the
        shared record recently, so the next in-window request does NOT hit
        the database."""
        # Record was refreshed moments ago by another worker.
        db = _make_db_factory(_FakeRecord(datetime.now()))
        sess = _make_session(db, refresh_time=60, last_access=_ago(120))

        self.assertTrue(sess.revalidate())
        self.assertEqual(db.calls["count"], 1)
        # Local timestamp advanced -> now within the window.
        self.assertTrue(sess.revalidate())
        self.assertEqual(db.calls["count"], 1)  # no extra DB query

    def test_db_write_skipped_when_record_recent(self):
        """The DB last_access write is skipped when another worker refreshed
        it recently, but the local timestamp still advances."""
        db = _make_db_factory(_FakeRecord(datetime.now()))
        sess = _make_session(db, refresh_time=60, last_access=_ago(120))
        self.assertTrue(sess.revalidate())
        self.assertFalse(db.transaction.committed)

    def test_db_write_when_record_stale(self):
        """The DB last_access write happens when the stored timestamp is
        older than refresh_time."""
        db = _make_db_factory(_FakeRecord(_ago(120)))
        sess = _make_session(db, refresh_time=60, last_access=_ago(120))
        self.assertTrue(sess.revalidate())
        self.assertTrue(db.transaction.committed)

    def test_refresh_time_zero_does_not_raise(self):
        """refresh_time 0 (-> internal None) must validate every call without
        raising, and still evict a deleted token."""
        db_ok = _make_db_factory(_FakeRecord(_ago(120)))
        sess_ok = _make_session(db_ok, refresh_time=0,
                                last_access=_ago(120))
        self.assertIsNone(sess_ok.refresh_time)
        self.assertTrue(sess_ok.revalidate())
        self.assertTrue(db_ok.transaction.committed)

        db_gone = _make_db_factory(None)
        sess_gone = _make_session(db_gone, refresh_time=0,
                                  last_access=_ago(120))
        self.assertFalse(sess_gone.revalidate())


class GetSessionEvictionTest(unittest.TestCase):
    """
    Tests that SessionManager.get_session() drops a cached session once its
    token is no longer valid in the database.
    """

    def _make_manager_with_cached_session(self, record):
        from codechecker_server.session_manager import SessionManager

        mgr = SessionManager.__new__(SessionManager)
        db = _make_db_factory(record)
        # last_access in the past -> refresh window elapsed -> DB is checked.
        sess = _make_session(db, refresh_time=60, last_access=_ago(120))
        mgr._SessionManager__sessions = [sess]
        mgr._SessionManager__database_connection = db
        mgr._SessionManager__auth_config = {"enabled": True}
        return mgr, sess

    def test_get_session_returns_valid_cached_session(self):
        mgr, sess = self._make_manager_with_cached_session(
            _FakeRecord(_ago(120)))
        self.assertIs(mgr.get_session(sess.token), sess)
        self.assertIn(sess, mgr._SessionManager__sessions)

    def test_get_session_evicts_stale_cached_session(self):
        mgr, sess = self._make_manager_with_cached_session(None)
        self.assertIsNone(mgr.get_session(sess.token))
        self.assertNotIn(sess, mgr._SessionManager__sessions)


if __name__ == "__main__":
    unittest.main()
