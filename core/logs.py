"""Save every live question to a small SQLite log (for monitoring and improving the semantic model)."""
import sqlite3
from datetime import datetime, timezone

from core.config import LOG_DB


def _conn():
    LOG_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(LOG_DB)
    con.execute("""CREATE TABLE IF NOT EXISTS query_log (
        ts TEXT, question TEXT, sql TEXT, ok INTEGER, rows INTEGER, error TEXT,
        attempts INTEGER, seconds REAL, provider TEXT, model TEXT, feedback TEXT)""")
    return con


def log_answer(ans, provider, model) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO query_log VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), ans.question, ans.sql,
             int(ans.ok), len(ans.rows), ans.error, ans.attempts, ans.seconds, provider, model))
        return cur.lastrowid


def save_feedback(row_id: int, feedback: str):
    with _conn() as con:
        con.execute("UPDATE query_log SET feedback = ? WHERE rowid = ?", (feedback, row_id))


def read_log(limit=500):
    with _conn() as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(
            "SELECT rowid AS id, * FROM query_log ORDER BY rowid DESC LIMIT ?", (limit,))]
