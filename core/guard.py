"""
SQL safety check: the AI may only READ data.
Rejects anything that is not a single SELECT (no INSERT/UPDATE/DELETE/DROP/ATTACH/COPY/PRAGMA...).
"""
import sqlglot
from sqlglot import exp

BLOCKED_FUNCTIONS = {"read_csv", "read_csv_auto", "read_parquet", "read_json", "read_json_auto",
                     "read_text", "read_blob", "glob", "sniff_csv"}


class UnsafeSQLError(ValueError):
    """The query tries to do something that is not allowed (never retried)."""


class SQLSyntaxError(ValueError):
    """The query is not valid SQL (the agent asks the AI to fix it)."""


def check_sql(sql: str, allowed_tables=None) -> str:
    sql = sql.strip().rstrip(";").strip()
    if not sql:
        raise SQLSyntaxError("Empty query")
    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except sqlglot.errors.ParseError as e:
        raise SQLSyntaxError(f"Could not parse SQL: {str(e).splitlines()[0]}")
    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise UnsafeSQLError("Only one SQL statement is allowed")
    stmt = statements[0]
    if not isinstance(stmt, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise UnsafeSQLError(f"Only SELECT queries are allowed (got {stmt.key.upper()})")
    cte_names = {c.alias_or_name.lower() for c in stmt.find_all(exp.CTE)}
    for node in stmt.walk():
        if allowed_tables is not None and isinstance(node, exp.Table) and node.name:
            name = node.name.lower()
            if name not in allowed_tables and name not in cte_names:
                raise UnsafeSQLError(f"Unknown table: {node.name}")
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
                             exp.Alter, exp.Command, exp.Copy)):
            raise UnsafeSQLError(f"Statement type {node.key.upper()} is not allowed")
        if isinstance(node, (exp.Anonymous, exp.Func)):
            name = (node.name if isinstance(node, exp.Anonymous) else node.sql_name()).lower()
            if name in BLOCKED_FUNCTIONS:
                raise UnsafeSQLError(f"Function {name} is not allowed")
    return sql
