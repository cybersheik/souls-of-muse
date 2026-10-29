import multiprocessing
import sqlite3
import unittest
import uuid
from pathlib import Path
from tempfile import mkdtemp

from runtime.admission import (
    AdmissionError,
    CapacityExceeded,
    InvalidTransition,
    LessonAdmission,
    initialize_database,
)


def _uid():
    return str(uuid.uuid4())


def _reserve_worker(db_path, result_queue):
    try:
        service = LessonAdmission(db_path)
        service.reserve(_uid(), _uid())
        result_queue.put('accepted')
    except CapacityExceeded:
        result_queue.put('capacity')
    except Exception as exc:  # pragma: no cover - reported by assertion below
        result_queue.put('error:' + type(exc).__name__)


def _exit_worker(code):
    raise SystemExit(code)


def _child_failures(processes):
    """Explicit per-child failure report; empty list means every child ok."""
    failures = []
    for index, process in enumerate(processes):
        if process.is_alive():
            failures.append(
                'child %d pid=%s still running after join timeout'
                % (index, process.pid)
            )
        elif process.exitcode != 0:
            failures.append(
                'child %d pid=%s exitcode=%r' % (index, process.pid, process.exitcode)
            )
    return failures


def _tables(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
    finally:
        conn.close()


class LessonAdmissionTests(unittest.TestCase):
    def make_service(self, capacity=5):
        # mkdtemp directories are intentionally preserved for inspection.
        directory = mkdtemp(prefix='cx1-lesson-')
        db_path = str(Path(directory) / 'lessons.db')
        service = initialize_database(db_path, capacity=capacity)
        return service, db_path

    def fill(self, service, count):
        rows = []
        for _ in range(count):
            rows.append(service.reserve(_uid(), _uid()))
        return rows

    def test_admission_control_concurrency_only_twelve_processes_five_slots(self):
        # ADMISSION CONTROL CONCURRENCY only: capacity=5 here is a test
        # fixture (one explicit operator configuration), not a product
        # limit and not a media/load benchmark; it does not claim five
        # real voice calls passed. spawn is used (never fork): forked
        # children crashed natively in this environment (AI3-935).
        _, db_path = self.make_service(capacity=5)
        ctx = multiprocessing.get_context('spawn')
        queue = ctx.Queue()
        processes = [
            ctx.Process(target=_reserve_worker, args=(db_path, queue))
            for _ in range(12)
        ]
        try:
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=60)
            failures = _child_failures(processes)
            self.assertEqual(
                failures, [],
                'every child must terminate with exitcode 0 before '
                'results are read; failures: %s' % (failures,),
            )
            results = []
            for _ in processes:
                try:
                    results.append(queue.get(timeout=5))
                except Exception as exc:
                    self.fail(
                        'child results missing after all children exited 0: '
                        '%r (collected %r)' % (exc, results)
                    )
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=10)
            queue.close()
            queue.join_thread()
        self.assertEqual(results.count('accepted'), 5)
        self.assertEqual(results.count('capacity'), 7)
        snapshot = LessonAdmission(db_path).snapshot()
        self.assertEqual(snapshot['active_count'], 5)
        self.assertEqual(snapshot['counts']['STARTING'], 5)

    def test_nonzero_child_exit_is_reported_explicitly(self):
        # Regression: an ordinary child exit(1) (never a native crash)
        # must surface as an explicit per-child failure, not a masked
        # queue timeout. If this detection ever breaks, this test fails
        # and the suite exits nonzero.
        ctx = multiprocessing.get_context('spawn')
        process = ctx.Process(target=_exit_worker, args=(1,))
        try:
            process.start()
            process.join(timeout=30)
        finally:
            if process.is_alive():
                process.terminate()
            process.join(timeout=10)
        self.assertFalse(process.is_alive())
        self.assertEqual(process.exitcode, 1)
        failures = _child_failures([process])
        self.assertEqual(len(failures), 1)
        self.assertIn('child 0', failures[0])
        self.assertIn('exitcode=1', failures[0])

    def test_normal_restart_preserves_five_starting(self):
        service, db_path = self.make_service(capacity=5)
        self.fill(service, 5)
        reopened = LessonAdmission(db_path)
        snapshot = reopened.snapshot()
        self.assertEqual(snapshot['counts']['STARTING'], 5)
        self.assertEqual(snapshot['active_count'], 5)
        with self.assertRaises(CapacityExceeded):
            reopened.reserve(_uid(), _uid())

    def test_last_closing_still_counts_until_confirm_closed(self):
        service, _ = self.make_service(capacity=1)
        row = service.reserve(_uid(), _uid())
        service.note_provision_started(row.reservation_id)
        service.mark_active(row.reservation_id)
        service.mark_closing(row.reservation_id)
        with self.assertRaises(CapacityExceeded):
            service.reserve(_uid(), _uid())
        service.confirm_closed(row.reservation_id)
        self.assertEqual(service.snapshot()['counts']['COMPLETED'], 1)
        service.reserve(_uid(), _uid())
        self.assertEqual(service.snapshot()['active_count'], 1)

    def test_timeout_uncertain_flag_set_cannot_cancel(self):
        service, _ = self.make_service(capacity=1)
        row = service.reserve(_uid(), _uid())
        service.note_provision_started(row.reservation_id)
        # Simulated uncertain external call: no automatic release occurs.
        with self.assertRaises(InvalidTransition):
            service.cancel_unprovisioned(row.reservation_id)
        self.assertEqual(service.snapshot()['counts']['STARTING'], 1)

    def test_cancel_preprovision_allows_next(self):
        service, _ = self.make_service(capacity=1)
        row = service.reserve(_uid(), _uid())
        cancelled = service.cancel_unprovisioned(row.reservation_id)
        self.assertEqual(cancelled.state, 'CANCELLED')
        service.reserve(_uid(), _uid())
        self.assertEqual(service.snapshot()['active_count'], 1)

    def test_duplicate_idempotent_repeated_same_pair_capacity_same(self):
        service, _ = self.make_service(capacity=1)
        lesson_id, request_id = _uid(), _uid()
        first = service.reserve(lesson_id, request_id)
        second = service.reserve(lesson_id, request_id)
        third = service.reserve(lesson_id, request_id)
        self.assertEqual(first.reservation_id, second.reservation_id)
        self.assertEqual(first.reservation_id, third.reservation_id)
        self.assertEqual(service.snapshot()['active_count'], 1)

    def test_request_id_reuse_with_different_lesson_rejected(self):
        service, _ = self.make_service()
        request_id = _uid()
        service.reserve(_uid(), request_id)
        with self.assertRaises(AdmissionError):
            service.reserve(_uid(), request_id)

    def test_different_request_for_same_lesson_and_terminal_reuse_rejected(self):
        service, _ = self.make_service()
        lesson_id = _uid()
        row = service.reserve(lesson_id, _uid())
        with self.assertRaises(AdmissionError):
            service.reserve(lesson_id, _uid())
        service.cancel_unprovisioned(row.reservation_id)
        with self.assertRaises(AdmissionError):
            service.reserve(lesson_id, _uid())

    def test_missing_and_corrupt_db_blocked(self):
        directory = mkdtemp(prefix='cx1-lesson-')
        missing = str(Path(directory) / 'missing.db')
        with self.assertRaises(AdmissionError):
            LessonAdmission(missing)
        corrupt = Path(directory) / 'corrupt.db'
        corrupt.write_bytes(b'this is not a sqlite database')
        with self.assertRaises(AdmissionError):
            LessonAdmission(str(corrupt))
        with self.assertRaises(AdmissionError):
            initialize_database(str(corrupt), capacity=5)

    def test_corrupt_capacity_and_invalid_states_blocked(self):
        # Corrupt stored capacity (non-positive / non-numeric) fails
        # closed. A merely larger positive value is no longer corrupt:
        # it can be a legitimate operator-selected capacity.
        service, db_path = self.make_service()
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "UPDATE admission_meta SET value='0' WHERE key='capacity'"
            )
            conn.commit()
        finally:
            conn.close()
        with self.assertRaises(AdmissionError):
            LessonAdmission(db_path)
        service0, db_path0 = self.make_service()
        conn = sqlite3.connect(db_path0)
        try:
            conn.execute(
                "UPDATE admission_meta SET value='not-a-number' "
                "WHERE key='capacity'"
            )
            conn.commit()
        finally:
            conn.close()
        with self.assertRaises(AdmissionError):
            LessonAdmission(db_path0)
        service2, db_path2 = self.make_service()
        service2.reserve(_uid(), _uid())
        conn = sqlite3.connect(db_path2)
        try:
            conn.execute("UPDATE reservations SET state='BOGUS'")
            conn.commit()
        finally:
            conn.close()
        with self.assertRaises(AdmissionError):
            LessonAdmission(db_path2)

    def test_capacity_above_five_is_an_operator_choice(self):
        # No product maximum remains: an operator may explicitly select
        # capacity for our own media workers above the old fixture of 5.
        _, db_path = self.make_service(capacity=5)
        with self.assertRaises(AdmissionError):
            LessonAdmission(db_path, capacity=6)
        directory = mkdtemp(prefix='cx1-lesson-')
        with self.assertRaises(AdmissionError):
            initialize_database(str(Path(directory) / 'y.db'), capacity=0)
        with self.assertRaises(AdmissionError):
            initialize_database(str(Path(directory) / 'z.db'), capacity=-3)
        with self.assertRaises(AdmissionError):
            initialize_database(str(Path(directory) / 'w.db'), capacity=True)
        service12, _ = self.make_service(capacity=12)
        self.fill(service12, 12)
        self.assertEqual(service12.snapshot()['capacity'], 12)
        self.assertEqual(service12.snapshot()['active_count'], 12)
        with self.assertRaises(CapacityExceeded):
            service12.reserve(_uid(), _uid())

    def test_fresh_database_requires_explicit_capacity(self):
        directory = mkdtemp(prefix='cx1-lesson-')
        db_path = str(Path(directory) / 'fresh.db')
        with self.assertRaises(AdmissionError):
            initialize_database(db_path)
        # The rejected attempt created no schema; explicit retry works.
        service = initialize_database(db_path, capacity=4)
        self.assertEqual(service.snapshot()['capacity'], 4)
        # Omitting capacity for an existing DB preserves stored capacity.
        again = initialize_database(db_path)
        self.assertEqual(again.snapshot()['capacity'], 4)

    def test_capacity_cannot_increase_by_restart(self):
        _, db_path = self.make_service(capacity=3)
        with self.assertRaises(AdmissionError):
            LessonAdmission(db_path, capacity=4)
        self.assertEqual(LessonAdmission(db_path).snapshot()['capacity'], 3)

    def test_race_initialize_existing_db_never_resets(self):
        service, db_path = self.make_service(capacity=2)
        row = service.reserve(_uid(), _uid())
        again = initialize_database(db_path, capacity=2)
        snapshot = again.snapshot()
        self.assertEqual(snapshot['active_count'], 1)
        self.assertEqual(
            snapshot['reservations'][0]['reservation_id'], row.reservation_id
        )

    def test_invalid_identifiers_reject(self):
        service, _ = self.make_service()
        bad_pairs = [
            ('short', _uid()),
            (_uid(), 'short'),
            ('person@example.com-123456', _uid()),
            (_uid(), 'token with spaces 123456'),
            ('\u00e9' * 20, _uid()),
            (_uid(), 'x' * 81),
        ]
        for lesson_id, request_id in bad_pairs:
            with self.assertRaises(AdmissionError):
                service.reserve(lesson_id, request_id)
        self.assertEqual(service.snapshot()['active_count'], 0)

    def test_unknown_reservation_reject(self):
        service, _ = self.make_service()
        unknown = _uid()
        for method in (
            service.note_provision_started,
            service.mark_active,
            service.mark_closing,
            service.confirm_closed,
            service.cancel_unprovisioned,
        ):
            with self.assertRaises(AdmissionError):
                method(unknown)

    def test_mark_active_requires_provision_flag(self):
        service, _ = self.make_service()
        row = service.reserve(_uid(), _uid())
        with self.assertRaises(InvalidTransition):
            service.mark_active(row.reservation_id)
        service.note_provision_started(row.reservation_id)
        active = service.mark_active(row.reservation_id)
        self.assertEqual(active.state, 'ACTIVE')
        self.assertTrue(active.provision_started)

    # Regressions from independent review.

    def test_trailing_newline_identifiers_rejected(self):
        service, _ = self.make_service()
        with self.assertRaises(AdmissionError):
            service.reserve('A' * 16 + '\n', _uid())
        with self.assertRaises(AdmissionError):
            service.reserve(_uid(), 'B' * 20 + '\n')
        self.assertEqual(service.snapshot()['active_count'], 0)

    def test_capacity_divergence_lower_and_initializer_mismatch_blocked(self):
        _, db_path = self.make_service(capacity=5)
        with self.assertRaises(AdmissionError):
            LessonAdmission(db_path, capacity=3)
        with self.assertRaises(AdmissionError):
            LessonAdmission(db_path, capacity=1)
        with self.assertRaises(AdmissionError):
            initialize_database(db_path, capacity=3)
        with self.assertRaises(AdmissionError):
            initialize_database(db_path, capacity=4)
        self.assertEqual(LessonAdmission(db_path, capacity=5).capacity, 5)
        self.assertEqual(LessonAdmission(db_path).snapshot()['capacity'], 5)
        _, db_path3 = self.make_service(capacity=3)
        with self.assertRaises(AdmissionError):
            LessonAdmission(db_path3, capacity=5)
        with self.assertRaises(AdmissionError):
            initialize_database(db_path3, capacity=5)

    def test_stored_capacity_change_after_construction_fails_closed(self):
        service, db_path = self.make_service(capacity=3)
        service.reserve(_uid(), _uid())
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "UPDATE admission_meta SET value='2' WHERE key='capacity'"
            )
            conn.commit()
        finally:
            conn.close()
        with self.assertRaises(AdmissionError):
            service.snapshot()
        with self.assertRaises(AdmissionError):
            service.reserve(_uid(), _uid())
        with self.assertRaises(AdmissionError):
            service.note_provision_started(_uid())

    def test_note_provision_started_only_starting_and_idempotent_there(self):
        service, _ = self.make_service(capacity=3)
        first = service.reserve(_uid(), _uid())
        noted = service.note_provision_started(first.reservation_id)
        self.assertEqual((noted.state, noted.provision_started), ('STARTING', True))
        again = service.note_provision_started(first.reservation_id)
        self.assertEqual((again.state, again.provision_started), ('STARTING', True))
        service.mark_active(first.reservation_id)
        with self.assertRaises(InvalidTransition):
            service.note_provision_started(first.reservation_id)
        service.mark_closing(first.reservation_id)
        with self.assertRaises(InvalidTransition):
            service.note_provision_started(first.reservation_id)
        second = service.reserve(_uid(), _uid())
        service.note_provision_started(second.reservation_id)
        service.mark_active(second.reservation_id)
        service.mark_closing(second.reservation_id)
        service.confirm_closed(second.reservation_id)
        with self.assertRaises(InvalidTransition):
            service.note_provision_started(second.reservation_id)
        third = service.reserve(_uid(), _uid())
        service.cancel_unprovisioned(third.reservation_id)
        with self.assertRaises(InvalidTransition):
            service.note_provision_started(third.reservation_id)

    def test_initializer_does_not_heal_partial_meta_only_schema(self):
        directory = mkdtemp(prefix='cx1-lesson-')
        db_path = str(Path(directory) / 'partial.db')
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                'CREATE TABLE admission_meta '
                '(key TEXT PRIMARY KEY, value TEXT NOT NULL)'
            )
            conn.executemany(
                'INSERT INTO admission_meta(key, value) VALUES (?, ?)',
                [('schema_version', '1'), ('capacity', '5'),
                 ('created_at_utc', '2024-01-01T00:00:00Z')],
            )
            conn.commit()
        finally:
            conn.close()
        before = Path(db_path).read_bytes()
        with self.assertRaises(AdmissionError):
            initialize_database(db_path, capacity=5)
        self.assertEqual(_tables(db_path), {'admission_meta'})
        self.assertEqual(Path(db_path).read_bytes(), before)

    def test_initializer_does_not_heal_reservations_only_or_unrelated(self):
        directory = mkdtemp(prefix='cx1-lesson-')
        reservations_only = str(Path(directory) / 'reservations-only.db')
        conn = sqlite3.connect(reservations_only)
        try:
            conn.execute(
                'CREATE TABLE reservations (reservation_id TEXT PRIMARY KEY '
                'NOT NULL, lesson_id TEXT NOT NULL UNIQUE, request_id TEXT '
                'NOT NULL UNIQUE, state TEXT NOT NULL, provision_started '
                'INTEGER NOT NULL DEFAULT 0, created_at_utc TEXT NOT NULL, '
                'updated_at_utc TEXT NOT NULL)'
            )
            conn.commit()
        finally:
            conn.close()
        before = Path(reservations_only).read_bytes()
        with self.assertRaises(AdmissionError):
            initialize_database(reservations_only, capacity=5)
        self.assertEqual(_tables(reservations_only), {'reservations'})
        self.assertEqual(Path(reservations_only).read_bytes(), before)
        unrelated = str(Path(directory) / 'unrelated.db')
        conn = sqlite3.connect(unrelated)
        try:
            conn.execute('CREATE TABLE unrelated (id INTEGER PRIMARY KEY, note TEXT)')
            conn.execute("INSERT INTO unrelated(note) VALUES ('keep me')")
            conn.commit()
        finally:
            conn.close()
        before = Path(unrelated).read_bytes()
        with self.assertRaises(AdmissionError):
            initialize_database(unrelated, capacity=5)
        self.assertEqual(_tables(unrelated), {'unrelated'})
        self.assertEqual(Path(unrelated).read_bytes(), before)

    def test_db_path_with_query_fragment_percent_and_spaces_opens_intended(self):
        directory = mkdtemp(prefix='cx1-lesson-')
        db_path = str(Path(directory) / 'les ?#% sons.db')
        service = initialize_database(db_path, capacity=2)
        service.reserve(_uid(), _uid())
        self.assertTrue(Path(db_path).is_file())
        reopened = LessonAdmission(db_path)
        self.assertEqual(reopened.snapshot()['active_count'], 1)
        self.assertEqual(reopened.snapshot()['capacity'], 2)

    def test_nul_db_path_rejected_before_opening(self):
        with self.assertRaises(AdmissionError):
            LessonAdmission('bad\x00lessons.db')
        with self.assertRaises(AdmissionError):
            initialize_database('bad\x00lessons.db', capacity=5)



    def test_relative_db_path_is_pinned_to_original_directory(self):
        # Regression for the relative-path defect found by Meta Spark.
        import os
        original_cwd = os.getcwd()
        base = Path(mkdtemp(prefix='cx1-lesson-'))
        other = Path(mkdtemp(prefix='cx1-lesson-'))
        try:
            os.chdir(base)
            initialized = initialize_database('lessons.db', capacity=2)
            reopened = LessonAdmission('lessons.db')
            os.chdir(other)
            initialized.reserve(_uid(), _uid())
            reopened.reserve(_uid(), _uid())
            self.assertEqual(initialized.snapshot()['active_count'], 2)
            self.assertEqual(reopened.snapshot()['active_count'], 2)
            self.assertFalse((other / 'lessons.db').exists())
            original = LessonAdmission(str(base / 'lessons.db'))
            self.assertEqual(original.snapshot()['active_count'], 2)
        finally:
            os.chdir(original_cwd)


if __name__ == '__main__':
    unittest.main()
