"""Safe, read-only database access."""
import threading

import duckdb

from core.config import DB_PATH, QUERY_TIMEOUT_SEC


def connect(path=None):
    """
    Open the database READ-ONLY with external access disabled,
    so a query can never change data or read files / URLs on the server.
    """
    return duckdb.connect(str(path or DB_PATH), read_only=True,
                          config={"enable_external_access": False})


def raw_schema(con) -> str:
    """Table and column names with types -- all the AI gets in 'raw' mode."""
    lines = []
    for (t,) in con.execute("SHOW TABLES").fetchall():
        cols = con.execute(f"DESCRIBE {t}").fetchall()
        lines.append(f"TABLE {t} (" + ", ".join(f"{c[0]} {c[1]}" for c in cols) + ")")
    return "\n".join(lines)


def run_query(con, sql, max_rows=None, timeout=QUERY_TIMEOUT_SEC):
    """Run SQL with a time limit. Returns (column_names, rows)."""
    timer = threading.Timer(timeout, con.interrupt)
    timer.start()
    try:
        cur = con.execute(sql)
        rows = cur.fetchmany(max_rows) if max_rows else cur.fetchall()
        cols = [d[0] for d in cur.description]
        return cols, rows
    except duckdb.InterruptException:
        raise TimeoutError(f"Query took longer than {timeout:.0f}s and was stopped")
    finally:
        timer.cancel()
