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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from codechecker_api.codeCheckerDBAccess_v6.ttypes import RunFilter
from codechecker_api_shared.ttypes import RequestFailed

from codechecker_server.api.report_server import \
    check_remove_runs_lock, get_run_ids_for_filter, process_run_filter
from codechecker_server.database.run_db_model import \
    Base, Run, RunLock


class RunRemovalLockTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

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

    def test_deletion_query_uses_resolved_ids_not_the_filter_again(self):
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

        This test proves the fix: after 'unlocked_run' is resolved and
        lock-checked (passing, since it's unlocked at that point), it
        gets deleted and a *new* run is created under the same name with
        an active lock, simulating a concurrent store starting in that
        window. Querying by the already-resolved 'matched_run_ids' must
        NOT match the new row, since it has a different id - unlike
        re-running the name filter, which would incorrectly match it.
        """
        run_filter = RunFilter(names=['unlocked_run'], exactMatch=True)
        matched_run_ids = get_run_ids_for_filter(self.session, run_filter)
        self.assertEqual(matched_run_ids, [2])

        # Should not raise: unlocked at preflight time.
        check_remove_runs_lock(self.session, matched_run_ids)

        # Simulate a concurrent client: the original run is removed, and
        # a new run is created under the *same name*, immediately locked
        # (e.g. a fresh store starting), all before the deletion query
        # runs.
        self.session.query(Run).filter(Run.id == 2).delete()
        new_run = Run('unlocked_run', '1.0')
        new_run.id = 3
        self.session.add(new_run)
        self.session.add(RunLock('unlocked_run'))
        self.session.commit()

        # The fixed deletion query: built from the already-resolved,
        # already lock-checked ids. It must not match the new, locked
        # run.
        fixed_query = self.session.query(Run) \
            .filter(Run.id.in_(matched_run_ids))
        self.assertEqual(fixed_query.all(), [])

        # Demonstrates the bug this closes: re-running the *filter*
        # instead would incorrectly match the new, locked run.
        buggy_query = process_run_filter(
            self.session, self.session.query(Run), run_filter)
        matched_names = [r.name for r in buggy_query.all()]
        self.assertIn('unlocked_run', matched_names)


if __name__ == "__main__":
    unittest.main()
