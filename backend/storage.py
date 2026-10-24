import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid() -> str:
    return uuid4().hex


class Store:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "patchgardener.sqlite3"
        with self.connect() as con:
            con.execute("CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, body TEXT, PRIMARY KEY(kind,id))")
            con.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, at TEXT, event TEXT, detail TEXT)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=20)

    def put(self, kind: str, record: dict):
        with self.connect() as con:
            con.execute("INSERT OR REPLACE INTO records VALUES(?,?,?)", (kind, record["id"], json.dumps(record)))

    def get(self, kind: str, key: str) -> dict:
        with self.connect() as con:
            row = con.execute("SELECT body FROM records WHERE kind=? AND id=?", (kind, key)).fetchone()
        if row is None:
            raise ValueError(f"Unknown {kind} ID")
        return json.loads(row[0])

    def audit(self, event: str, detail: dict):
        with self.connect() as con:
            con.execute("INSERT INTO audit(at,event,detail) VALUES(?,?,?)", (now(), event, json.dumps(detail)))

    def events(self) -> list[dict]:
        with self.connect() as con:
            rows = con.execute("SELECT id,at,event,detail FROM audit ORDER BY id DESC LIMIT 100").fetchall()
        return [{"id": row[0], "at": row[1], "event": row[2], "detail": json.loads(row[3])} for row in rows]
