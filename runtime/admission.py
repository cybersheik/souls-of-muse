"""Durable admission control for at most five simultaneous lessons.

SQLite is supported only on a single persistent VM whose processes share
one database file. This module controls lesson slots only; it does not
provide media, room, ASR, or video runtime behaviour. It is internal
only and must not be exposed as a public unauthenticated endpoint.
"""
from __future__ import annotations

import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

MAX_CAPACITY = 5
SCHEMA_VERSION = '1'
ACTIVE_STATES = ('STARTING', 'ACTIVE', 'CLOSING')
ALL_STATES = ACTIVE_STATES + ('COMPLETED', 'CANCELLED')
_LESSON_RE = re.compile(r'[A-Za-z0-9_-]{16,80}')
_REQUEST_RE = re.compile(r'[A-Za-z0-9_-]{20,80}')
_EXPECTED_COLUMNS = {
    'admission_meta': ['key', 'value'],
    'reservations': [
        'reservation_id', 'lesson_id', 'request_id', 'state',
        'provision_started', 'created_at_utc', 'updated_at_utc',
    ],
}


class AdmissionError(Exception):
    """Base error for admission-control failures."""


class CapacityExceeded(AdmissionError):
    """Raised before external calls when all counted slots are in use."""


class InvalidTransition(AdmissionError):
    """Raised when a lifecycle transition is not allowed."""


@dataclass(frozen=True)
class Reservation:
    reservation_id: str
    lesson_id: str
    request_id: str
    state: str
    provision_started: bool
    created_at_utc: str
    updated_at_utc: str

    def to_dict(self):
        return asdict(self)


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _check_capacity(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise AdmissionError('capacity must be an integer')
    if value < 1 or value > MAX_CAPACITY:
        raise AdmissionError('capacity must be between 1 and 5')
    return value


def _check_lesson_id(value):
    if not isinstance(value, str) or not _LESSON_RE.fullmatch(value):
        raise AdmissionError('lesson_id must be ASCII token of 16..80 chars')


def _check_request_id(value):
    if not isinstance(value, str) or not _REQUEST_RE.fullmatch(value):
        raise AdmissionError('request_id must be UUID or ASCII token 20..80')


def _check_reservation_id(value):
    if not isinstance(value, str):
        raise AdmissionError('reservation_id must be a UUID')
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise AdmissionError('reservation_id must be a UUID')


def _checked_path_text(db_path):
    if isinstance(db_path, Path):
        text = str(db_path)
    elif isinstance(db_path, str):
        text = db_path
    else:
        raise AdmissionError('db_path must be a path string')
    if not text or '\x00' in text:
        raise AdmissionError('db_path must not be empty or contain NUL')
    return text


def _resolved_path_text(db_path):
    text = _checked_path_text(db_path)
    try:
        return str(Path(text).resolve())
    except (ValueError, RuntimeError, OSError) as exc:
        raise AdmissionError('db_path cannot be resolved') from exc


def _file_uri(db_path, create=False):
    text = _checked_path_text(db_path)
    try:
        uri = Path(text).as_uri()
    except (ValueError, RuntimeError, OSError) as exc:
        raise AdmissionError('db_path cannot be resolved') from exc
    return uri + ('?mode=rwc' if create else '?mode=rw')


@contextmanager
def _connection(db_path, create=False):
    uri = _file_uri(db_path, create=create)
    conn = None
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA busy_timeout = 30000')
        conn.execute('PRAGMA foreign_keys = ON')
        yield conn
    except AdmissionError:
        raise
    except sqlite3.Error as exc:
        if conn is not None:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
        raise AdmissionError('database unavailable or corrupt') from exc
    finally:
        if conn is not None:
            conn.close()


def _safe_rollback(conn):
    try:
        conn.rollback()
    except sqlite3.Error:
        pass


def _row_to_reservation(row):
    return Reservation(
        reservation_id=row['reservation_id'],
        lesson_id=row['lesson_id'],
        request_id=row['request_id'],
        state=row['state'],
        provision_started=bool(row['provision_started']),
        created_at_utc=row['created_at_utc'],
        updated_at_utc=row['updated_at_utc'],
    )


def _user_tables(conn):
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    }


def _validate_database(conn):
    tables = _user_tables(conn)
    if 'admission_meta' not in tables or 'reservations' not in tables:
        raise AdmissionError('database schema is missing; run initializer')
    for table, expected in _EXPECTED_COLUMNS.items():
        columns = [
            row[1] for row in conn.execute('PRAGMA table_info(' + table + ')')
        ]
        if columns != expected:
            raise AdmissionError('database schema is invalid')
    meta = {
        row['key']: row['value']
        for row in conn.execute('SELECT key, value FROM admission_meta')
    }
    if meta.get('schema_version') != SCHEMA_VERSION:
        raise AdmissionError('unknown database schema version')
    try:
        stored = int(meta.get('capacity', ''))
    except (TypeError, ValueError):
        raise AdmissionError('stored capacity is invalid')
    if stored < 1 or stored > MAX_CAPACITY:
        raise AdmissionError('stored capacity is outside 1..5')
    rows = conn.execute(
        'SELECT state, provision_started, lesson_id, request_id, '
        'reservation_id FROM reservations'
    ).fetchall()
    seen_lessons = set()
    seen_requests = set()
    seen_reservations = set()
    for row in rows:
        if row['state'] not in ALL_STATES:
            raise AdmissionError('stored reservation state is invalid')
        if row['provision_started'] not in (0, 1):
            raise AdmissionError('stored provision flag is invalid')
        _check_lesson_id(row['lesson_id'])
        _check_request_id(row['request_id'])
        _check_reservation_id(row['reservation_id'])
        if row['lesson_id'] in seen_lessons:
            raise AdmissionError('stored lesson_id is duplicated')
        if row['request_id'] in seen_requests:
            raise AdmissionError('stored request_id is duplicated')
        if row['reservation_id'] in seen_reservations:
            raise AdmissionError('stored reservation_id is duplicated')
        seen_lessons.add(row['lesson_id'])
        seen_requests.add(row['request_id'])
        seen_reservations.add(row['reservation_id'])
    return stored


_SCHEMA = (
    'CREATE TABLE admission_meta ('
    ' key TEXT PRIMARY KEY, value TEXT NOT NULL)',
    'CREATE TABLE reservations ('
    ' reservation_id TEXT PRIMARY KEY NOT NULL,'
    ' lesson_id TEXT NOT NULL UNIQUE,'
    ' request_id TEXT NOT NULL UNIQUE,'
    ' state TEXT NOT NULL,'
    ' provision_started INTEGER NOT NULL DEFAULT 0'
    ' CHECK (provision_started IN (0, 1)),'
    ' created_at_utc TEXT NOT NULL,'
    ' updated_at_utc TEXT NOT NULL)',
)


def initialize_database(db_path, capacity=MAX_CAPACITY):
    """Explicit operator action: create a fresh DB or validate an existing one.

    Creation happens in one BEGIN IMMEDIATE transaction only when the
    file has no user tables. Any non-empty partial or unrelated schema
    is validated without DDL and fails closed if invalid; it is never
    healed and its stored capacity is never changed. An explicit
    capacity that differs from stored capacity always fails.
    """
    _check_capacity(capacity)
    path = _resolved_path_text(db_path)
    with _connection(path, create=True) as conn:
        try:
            conn.execute('BEGIN IMMEDIATE')
            tables = _user_tables(conn)
            if not tables:
                for statement in _SCHEMA:
                    conn.execute(statement)
                now = _utc_now()
                conn.execute(
                    'INSERT INTO admission_meta(key, value) VALUES (?, ?)',
                    ('schema_version', SCHEMA_VERSION),
                )
                conn.execute(
                    'INSERT INTO admission_meta(key, value) VALUES (?, ?)',
                    ('capacity', str(capacity)),
                )
                conn.execute(
                    'INSERT INTO admission_meta(key, value) VALUES (?, ?)',
                    ('created_at_utc', now),
                )
                stored = _validate_database(conn)
                if stored != capacity:
                    raise AdmissionError('capacity mismatch with existing database')
                conn.commit()
            else:
                stored = _validate_database(conn)
                if stored != capacity:
                    raise AdmissionError('capacity mismatch with existing database')
                _safe_rollback(conn)
        except AdmissionError:
            _safe_rollback(conn)
            raise
        except sqlite3.Error as exc:
            _safe_rollback(conn)
            raise AdmissionError('database initialization failed') from exc
    return LessonAdmission(path)


class LessonAdmission:
    """Normal-run admission service. Opening never creates a database."""

    def __init__(self, db_path, capacity=None):
        requested = None if capacity is None else _check_capacity(capacity)
        self.db_path = _resolved_path_text(db_path)
        with _connection(self.db_path) as conn:
            stored = _validate_database(conn)
        if requested is not None and requested != stored:
            raise AdmissionError('capacity mismatch with stored capacity')
        self._capacity = stored
        self._stored_capacity = stored

    @property
    def capacity(self):
        return self._capacity

    def _effective(self, stored):
        if stored != self._stored_capacity:
            raise AdmissionError('stored capacity changed after construction')
        return stored

    def _fetch(self, conn, reservation_id):
        row = conn.execute(
            'SELECT * FROM reservations WHERE reservation_id = ?',
            (reservation_id,),
        ).fetchone()
        if row is None:
            raise AdmissionError('unknown reservation')
        return _row_to_reservation(row)

    def reserve(self, lesson_id, request_id):
        """Reserve one counted slot, or raise CapacityExceeded.

        Idempotent in the database only for the same
        (lesson_id, request_id) pair. This does not claim exactly-once
        external effects; see README for the single-orchestrator and
        deterministic external identity requirements. A lesson_id is
        one-per-lesson and is never reused, including after a terminal
        state, so stored history is never overwritten.
        """
        _check_lesson_id(lesson_id)
        _check_request_id(request_id)
        with _connection(self.db_path) as conn:
            try:
                conn.execute('BEGIN IMMEDIATE')
                stored = _validate_database(conn)
                capacity = self._effective(stored)
                by_request = conn.execute(
                    'SELECT * FROM reservations WHERE request_id = ?',
                    (request_id,),
                ).fetchone()
                if by_request is not None:
                    existing = _row_to_reservation(by_request)
                    if existing.lesson_id != lesson_id:
                        raise AdmissionError(
                            'request_id already used for another lesson'
                        )
                    conn.commit()
                    return existing
                by_lesson = conn.execute(
                    'SELECT * FROM reservations WHERE lesson_id = ?',
                    (lesson_id,),
                ).fetchone()
                if by_lesson is not None:
                    raise AdmissionError('lesson_id already has a reservation')
                active = conn.execute(
                    'SELECT COUNT(*) FROM reservations WHERE state IN (?, ?, ?)',
                    ACTIVE_STATES,
                ).fetchone()[0]
                if active >= capacity:
                    raise CapacityExceeded('all lesson slots are in use')
                now = _utc_now()
                row = Reservation(
                    reservation_id=str(uuid.uuid4()),
                    lesson_id=lesson_id,
                    request_id=request_id,
                    state='STARTING',
                    provision_started=False,
                    created_at_utc=now,
                    updated_at_utc=now,
                )
                conn.execute(
                    'INSERT INTO reservations(reservation_id, lesson_id, '
                    'request_id, state, provision_started, created_at_utc, '
                    'updated_at_utc) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (row.reservation_id, row.lesson_id, row.request_id,
                     row.state, 0, row.created_at_utc, row.updated_at_utc),
                )
                conn.commit()
                return row
            except AdmissionError:
                _safe_rollback(conn)
                raise
            except sqlite3.Error as exc:
                _safe_rollback(conn)
                raise AdmissionError('reserve failed') from exc

    def _transition(self, reservation_id, action):
        _check_reservation_id(reservation_id)
        with _connection(self.db_path) as conn:
            try:
                conn.execute('BEGIN IMMEDIATE')
                stored = _validate_database(conn)
                self._effective(stored)
                current = self._fetch(conn, reservation_id)
                new_state, new_flag = action(current)
                conn.execute(
                    'UPDATE reservations SET state = ?, provision_started = ?, '
                    'updated_at_utc = ? WHERE reservation_id = ?',
                    (new_state, 1 if new_flag else 0, _utc_now(), reservation_id),
                )
                result = self._fetch(conn, reservation_id)
                conn.commit()
                return result
            except AdmissionError:
                _safe_rollback(conn)
                raise
            except sqlite3.Error as exc:
                _safe_rollback(conn)
                raise AdmissionError('transition failed') from exc

    def note_provision_started(self, reservation_id):
        """Durably record that an external provisioning attempt is starting.

        Call this BEFORE any room API call. Only STARTING may enter or
        repeat this step; ACTIVE, CLOSING and terminal states fail.
        Once set, cancellation is no longer allowed because the
        external outcome may be uncertain.
        """
        def action(current):
            if current.state != 'STARTING':
                raise InvalidTransition('provision can only start from STARTING')
            return 'STARTING', True
        return self._transition(reservation_id, action)

    def mark_active(self, reservation_id):
        """Move STARTING to ACTIVE, only after provisioning was noted."""
        def action(current):
            if current.state == 'ACTIVE' and current.provision_started:
                return current.state, True
            if current.state != 'STARTING' or not current.provision_started:
                raise InvalidTransition('active requires provision_started')
            return 'ACTIVE', True
        return self._transition(reservation_id, action)

    def mark_closing(self, reservation_id):
        """Move STARTING/ACTIVE to CLOSING; the slot remains counted."""
        def action(current):
            if current.state == 'CLOSING':
                return current.state, current.provision_started
            if current.state not in ('STARTING', 'ACTIVE'):
                raise InvalidTransition('only STARTING or ACTIVE can close')
            return 'CLOSING', current.provision_started
        return self._transition(reservation_id, action)

    def confirm_closed(self, reservation_id):
        """Move CLOSING to COMPLETED after confirmed external cleanup.

        This method is not proof of external cleanup itself. The trusted
        caller is responsible for confirming the external room is deleted
        before calling it. Only then is the counted slot freed.
        """
        def action(current):
            if current.state != 'CLOSING':
                raise InvalidTransition('only CLOSING can be confirmed closed')
            return 'COMPLETED', current.provision_started
        return self._transition(reservation_id, action)

    def cancel_unprovisioned(self, reservation_id):
        """Cancel only a STARTING reservation with no provisioning attempt."""
        def action(current):
            if current.state != 'STARTING' or current.provision_started:
                raise InvalidTransition('cannot cancel after provisioning starts')
            return 'CANCELLED', False
        return self._transition(reservation_id, action)

    def snapshot(self):
        """Return stable counts and reservations; no credentials are stored."""
        with _connection(self.db_path) as conn:
            stored = _validate_database(conn)
            capacity = self._effective(stored)
            rows = conn.execute(
                'SELECT * FROM reservations ORDER BY created_at_utc, '
                'reservation_id'
            ).fetchall()
        reservations = [_row_to_reservation(row).to_dict() for row in rows]
        counts = {state: 0 for state in ALL_STATES}
        for item in reservations:
            counts[item['state']] += 1
        active = sum(counts[state] for state in ACTIVE_STATES)
        return {
            'capacity': capacity,
            'active_count': active,
            'counts': counts,
            'reservations': reservations,
        }
