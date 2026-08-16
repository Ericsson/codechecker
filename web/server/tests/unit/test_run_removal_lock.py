# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Regression tests for https://github.com/Ericsson/codechecker/issues/1445 -
run deletion should be rejected while an active RunLock exists for the
run(s) being removed.

Previously, 'removeRun()' called 'check_remove_runs_lock(session,
[run_id])'. Callers that select runs via 'run_filter' instead of a numeric
id - such as the CLI's "CodeChecker cmd del" command, which always calls
'removeRun(None, run_filter)' - passed 'run_id=None', so the lock check
received '[None]'. Since no run ever has 'id IS NULL', this silently
matched nothing and bypassed the lock check entirely, regardless of
whether the targeted run(s) were actually locked.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from codechecker_api.codeCheckerDBAccess_v6.ttypes import RunFilter
from codechecker_api_shared.ttypes import RequestFailed

from codechecker_server.api.report_server import \
    ThriftRequestHandler, check_remove_runs_lock, get_run_ids_for_filter
from codechecker_server.database.run_db_model import \
    Base, Run, RunLock


class RunRemovalLockTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            'sqlite:///:memory:',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.session = self.session_factory()

        run1 = Run('locked_run', '1.0')
        run1.id = 1
        run2 = Run('unlocked_run', '1.0')
        run2.id = 2
        self.session.add(run1)
        self.session.add(run2)
        self.session.commit()

        self.session.add(RunLock('locked_run'))
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_run_id_none_no_longer_bypasses_lock_check(self):
        """
        This is the exact bug from #1445: resolving run ids via a
        name-based filter (as the CLI does, always calling removeRun with
        run_id=None) must still correctly detect an active lock, instead
        of silently checking against '[None]'.
        """
        run_filter = RunFilter(names=['locked_run'], exactMatch=True)

        matched_run_ids = get_run_ids_for_filter(self.session, run_filter)
        self.assertEqual(matched_run_ids, [1])

        with self.assertRaises(RequestFailed):
            check_remove_runs_lock(self.session, matched_run_ids)

    def test_unlocked_run_is_not_blocked(self):
        run_filter = RunFilter(names=['unlocked_run'], exactMatch=True)

        matched_run_ids = get_run_ids_for_filter(self.session, run_filter)
        self.assertEqual(matched_run_ids, [2])

        # Should not raise.
        check_remove_runs_lock(self.session, matched_run_ids)

    def test_old_buggy_call_pattern_would_have_missed_the_lock(self):
        """
        Documents the actual root cause: calling the lock check with
        '[run_id]' where run_id is None (the old removeRun behavior for
        any filter-based deletion) never detects any lock, no matter what
        is actually locked.
        """
        check_remove_runs_lock(self.session, [None])  # Should not raise.

    def test_expired_lock_does_not_block_removal(self):
        stale_lock = self.session.query(RunLock) \
            .filter(RunLock.name == 'locked_run').one()
        stale_lock.locked_at = datetime.now() - timedelta(hours=1)
        self.session.commit()

        run_filter = RunFilter(names=['locked_run'], exactMatch=True)
        matched_run_ids = get_run_ids_for_filter(self.session, run_filter)

        # Should not raise: the lock is old enough to be considered
        # expired/stale.
        check_remove_runs_lock(self.session, matched_run_ids)

    def test_remove_run_does_not_delete_a_run_recreated_during_the_call(
            self):
        """
        Regression test for
        https://github.com/Ericsson/codechecker/issues/5031

        This is a follow-up to #1445/#4999: 'removeRun' resolves
        'matched_run_ids' from the filter and lock-checks those ids, but
        previously re-ran the *filter* (not the resolved ids) to build
        the actual destructive query. Since each delete commits in its
        own transaction, a run recreated under the same name between the
        lock check and the deletion - now holding a fresh, active lock -
        would still match the filter and get deleted without ever being
        lock-checked.

        Unlike a test that re-implements the query being fixed, this
        exercises the real 'removeRun()' method end-to-end: 'run_filter'
        resolution is intercepted at exactly the point 'removeRun' calls
        it, and a concurrent removal + recreation of 'unlocked_run' under
        the same name (now with an active lock) is simulated right after
        the real lock check has passed - simulating a second client
        racing in between. The new, locked run must survive the call.
        """
        run_filter = RunFilter(names=['unlocked_run'], exactMatch=True)
        real_get_run_ids_for_filter = get_run_ids_for_filter

        prev_run_id = None

        def resolve_then_simulate_concurrent_removal(session, rf):
            nonlocal prev_run_id
            ids = real_get_run_ids_for_filter(session, rf)

            concurrent_session = self.session_factory()
            prev_run_id = concurrent_session.query(Run).filter(
                Run.name == 'unlocked_run').first().id
            concurrent_session.query(Run).filter(
                Run.name == 'unlocked_run').delete()
            new_run = Run('unlocked_run', '1.0')
            new_run.id = prev_run_id + 1
            concurrent_session.add(new_run)
            concurrent_session.add(RunLock('unlocked_run'))
            concurrent_session.commit()
            concurrent_session.close()

            return ids

        handler = ThriftRequestHandler.__new__(ThriftRequestHandler)
        handler._Session = self.session_factory
        handler._product = MagicMock()
        handler._config_database = MagicMock()
        handler._auth_session = None

        with patch.object(
                ThriftRequestHandler, '_ThriftRequestHandler__require_store',
                lambda self: None), \
                patch('codechecker_server.api.report_server.db_cleanup'
                      '.remove_unused_comments'), \
                patch('codechecker_server.api.report_server.db_cleanup'
                      '.remove_unused_analysis_info'), \
                patch('codechecker_server.api.report_server'
                      '.get_run_ids_for_filter',
                      side_effect=resolve_then_simulate_concurrent_removal):
            handler.removeRun(None, run_filter)

        verify_session = self.session_factory()
        remaining = verify_session.query(Run).filter(
            Run.id == prev_run_id + 1).all()
        verify_session.close()

        self.assertEqual(
            len(remaining), 1,
            "The run recreated (with an active lock) during the "
            "removeRun() call was incorrectly deleted.")


if __name__ == "__main__":
    unittest.main()
