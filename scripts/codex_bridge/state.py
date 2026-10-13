"""Single-installation lock, durable receipts and append-only bounded events."""

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import sqlite3

from .schema import Rejected, canonical

TERMINAL = {"SUCCEEDED", "FAILED", "BLOCKED", "CANCELLED"}


@contextmanager
def installation_lock(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "bridge.lock").open("a+b") as handle:
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise Rejected("ALREADY_RUNNING") from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


class Journal:
    def __init__(self, directory, max_events=10000, max_bytes=16 * 1024 * 1024):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.max_events, self.max_bytes = max_events, max_bytes
        self.db = sqlite3.connect(self.directory / "journal.sqlite3", isolation_level=None)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_key TEXT PRIMARY KEY, nonce_key TEXT UNIQUE NOT NULL,
                idempotency_key TEXT UNIQUE NOT NULL, issue_id INTEGER UNIQUE NOT NULL,
                issue_number INTEGER UNIQUE NOT NULL, fingerprint TEXT NOT NULL,
                state TEXT NOT NULL, lease_until REAL NOT NULL, started REAL
            );
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, task_key TEXT,
                state TEXT NOT NULL, at REAL NOT NULL, reason TEXT NOT NULL
            );
            CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
                BEGIN SELECT RAISE(ABORT, 'append-only'); END;
            CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
                BEGIN SELECT RAISE(ABORT, 'append-only'); END;
            CREATE TABLE IF NOT EXISTS outbox (
                result_id TEXT PRIMARY KEY, issue_number INTEGER NOT NULL,
                body TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0
            );
        """)

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def event(self, task_key, state, now, reason):
        count = self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        size = self.db.execute("PRAGMA page_count").fetchone()[0] * self.db.execute("PRAGMA page_size").fetchone()[0]
        if count >= self.max_events or size + 8192 > self.max_bytes:
            raise Rejected("JOURNAL_CAPACITY")
        self.db.execute("INSERT INTO events(task_key,state,at,reason) VALUES(?,?,?,?)",
                        (task_key, state, now, reason))

    def reject(self, now, reason="INVALID_TASK"):
        # Never persist raw payloads, exception strings or unvalidated identifiers.
        with self.transaction():
            self.event(None, "BLOCKED", now, reason)

    def reserve(self, task, now):
        with self.transaction():
            if self.db.execute("SELECT 1 FROM tasks WHERE state IN ('CLAIMED','RUNNING')").fetchone():
                raise Rejected("BUSY")
            try:
                self.db.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,NULL)",
                                (task.task_key, task.nonce_key, task.idempotency_key,
                                 task.issue_id, task.number, task.fingerprint, "CLAIMED",
                                 min(task.expires, now + task.lease_seconds)))
            except sqlite3.IntegrityError:
                raise Rejected("REPLAY") from None
            for state in ("NEW", "VALIDATED", "CLAIMED"):
                self.event(task.task_key, state, now, "OFFLINE_TASK")

    def start(self, task, now):
        with self.transaction():
            row = self.db.execute("SELECT state,lease_until FROM tasks WHERE task_key=?", (task.task_key,)).fetchone()
            if row is None or row[0] != "CLAIMED" or row[1] <= now:
                raise Rejected("LEASE_EXPIRED")
            self.event(task.task_key, "RUNNING", now, "FAKE_EXECUTOR")
            self.db.execute("UPDATE tasks SET state='RUNNING',started=? WHERE task_key=?", (now, task.task_key))
        return row[1]

    def finish(self, task_key, state, now, reason, exit_code=None, output_sha256=None):
        if state not in TERMINAL:
            raise ValueError("invalid terminal state")
        with self.transaction():
            row = self.db.execute("SELECT issue_number,started,state FROM tasks WHERE task_key=?", (task_key,)).fetchone()
            if row is None or row[2] not in {"CLAIMED", "RUNNING"}:
                raise Rejected("STATE_CONFLICT")
            self.event(task_key, state, now, reason)
            self.db.execute("UPDATE tasks SET state=? WHERE task_key=?", (state, task_key))
            result_id = hashlib.sha256(f"{task_key}:{state}".encode()).hexdigest()
            body = canonical({"result_id": result_id, "task_key": task_key,
                              "state": state, "exit_code": exit_code,
                              "output_sha256": output_sha256,
                              "started_at": row[1], "ended_at": now,
                              "evidence_mode": "OFFLINE_FAKE_EXECUTOR"})
            self.db.execute("INSERT INTO outbox(result_id,issue_number,body) VALUES(?,?,?)",
                            (result_id, row[0], body))

    def recover(self, now):
        rows = self.db.execute("SELECT task_key FROM tasks WHERE state IN ('CLAIMED','RUNNING')").fetchall()
        for (task_key,) in rows:
            self.finish(task_key, "BLOCKED", now, "RESTART_UNCERTAIN")

    def pending(self):
        return self.db.execute("SELECT result_id,issue_number,body FROM outbox WHERE delivered=0 ORDER BY rowid").fetchall()

    def delivered(self, result_id, now):
        with self.transaction():
            self.event(None, "PUBLISHED", now, "RESULT_RECONCILED")
            self.db.execute("UPDATE outbox SET delivered=1 WHERE result_id=?", (result_id,))
