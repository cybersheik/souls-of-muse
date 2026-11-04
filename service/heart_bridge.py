"""Durable runtime outbox delivered to Kimi's original signed journal."""
import json
import threading
import uuid
from pathlib import Path

from heart import journal


class HeartBridge:
    def __init__(self, db, commit, data_dir, private_key=None):
        self.db = db
        self.commit = commit
        self.path = str(Path(data_dir) / "heart.sqlite3")
        self.key = private_key
        self.lock = threading.Lock()
        c = db()
        try:
            c.executescript("""
              CREATE TABLE IF NOT EXISTS heart_outbox(event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                  event_json TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending', reason TEXT);
              CREATE TABLE IF NOT EXISTS session_presence(session_id TEXT NOT NULL, participant TEXT NOT NULL,
                  PRIMARY KEY(session_id, participant));
            """)
            commit(c)
        finally:
            c.close()
        heart = journal.init_db(self.path)
        heart.close()

    @staticmethod
    def group_policy_pending(c, session_id):
        # The signed journal defines pairs. A group must not silently become
        # Maestro + its first Artist, or award Maestro once per child.
        row = c.execute("SELECT s.kind, (SELECT COUNT(*) FROM session_members m WHERE m.session_id=s.id AND m.role='artist') AS artists FROM sessions s WHERE s.id=?", (session_id,)).fetchone()
        return bool(row and row["kind"] == "group" and row["artists"] > 1)

    def enqueue_completion(self, c, session, now):
        if self.group_policy_pending(c, session["id"]):
            return
        people = [session["maestro_id"], session["artist_id"]]
        if not all(people):
            return
        present = {r[0] for r in c.execute("SELECT participant FROM session_presence WHERE session_id=?", (session["id"],))}
        if not set(people).issubset(present):
            return
        for seq, (person, other) in enumerate([people, people[::-1]], 1):
            event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"som:{session['id']}:completed:{person}"))
            event = {"event_id": event_id, "lesson_id": session["id"], "seq": seq, "ts": now,
                     "type": "lesson.completed", "actor": "server",
                     "payload": {"soul_id": person, "counterparty": other}}
            c.execute("INSERT OR IGNORE INTO heart_outbox(event_id,session_id,event_json) VALUES(?,?,?)",
                      (event_id, session["id"], json.dumps(event, ensure_ascii=False)))

    def drain(self):
        if self.key is None:
            return
        with self.lock:
            c = self.db()
            heart = journal.init_db(self.path)
            try:
                for row in c.execute("SELECT event_id,session_id,event_json FROM heart_outbox WHERE state='pending' ORDER BY rowid").fetchall():
                    if self.group_policy_pending(c, row["session_id"]):
                        # Preserve an old runtime event as rejected; never send
                        # it into Kimi's immutable signed pair journal.
                        c.execute("UPDATE heart_outbox SET state='rejected',reason='group_policy_pending' WHERE event_id=?", (row["event_id"],))
                        self.commit(c)
                        continue
                    try:
                        journal.append_event(heart, json.loads(row["event_json"]), self.key)
                        # Persist the journal before marking the outbox delivered. A crash
                        # between these writes retries the same event_id safely.
                        self.commit(c)
                    except journal.Rejected as exc:
                        c.execute("UPDATE heart_outbox SET state='rejected',reason=? WHERE event_id=?", (exc.reason, row["event_id"]))
                    else:
                        c.execute("UPDATE heart_outbox SET state='delivered',reason=NULL WHERE event_id=?", (row["event_id"],))
                    self.commit(c)
            finally:
                heart.close()
                c.close()

    def state(self, c, session_id, participant):
        heart = journal.init_db(self.path)
        try:
            result = journal.counters(heart, participant)
        finally:
            heart.close()
        rows = c.execute("SELECT state,reason FROM heart_outbox WHERE session_id=?", (session_id,)).fetchall()
        pending = self.group_policy_pending(c, session_id)
        return {"counters": result, "delivery": [dict(row) for row in rows], "signing_ready": self.key is not None,
                "accrual": {"supported": not pending, "state": "group_policy_pending" if pending else "pair_policy"}}
