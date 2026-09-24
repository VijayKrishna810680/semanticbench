"""Run with: pytest -q   (needs the database: python setup_data.py)"""
import json

import pytest

from analyze import classify
from core.checker import is_correct
from core.config import DB_PATH, QUESTIONS_FILE
from core.guard import SQLSyntaxError, UnsafeSQLError, check_sql

needs_db = pytest.mark.skipif(not DB_PATH.exists(), reason="run python setup_data.py first")
TABLES = {"orders", "customers", "order_items", "products", "sellers", "order_payments",
          "order_reviews", "category_translation"}


# ---------------- safety guard
@pytest.mark.parametrize("sql", [
    "SELECT COUNT(*) FROM orders",
    "WITH x AS (SELECT 1 AS a) SELECT * FROM x",
    "SELECT order_status FROM orders UNION SELECT 'x'",
])
def test_guard_allows_reads(sql):
    assert check_sql(sql, TABLES)


@pytest.mark.parametrize("sql", [
    "DROP TABLE orders", "DELETE FROM orders", "UPDATE orders SET order_status = 'x'",
    "INSERT INTO orders VALUES (1)", "SELECT 1; DROP TABLE orders", "ATTACH 'other.db'",
    "COPY orders TO 'out.csv'", "PRAGMA database_list", "SELECT * FROM read_csv('/etc/passwd')",
    "SELECT * FROM 'data/raw/olist_orders_dataset.csv'", "SELECT * FROM secret_table",
])
def test_guard_blocks_unsafe(sql):
    with pytest.raises(UnsafeSQLError):
        check_sql(sql, TABLES)


def test_guard_syntax_error_is_retryable():
    with pytest.raises(SQLSyntaxError):
        check_sql("SELEC FROM", TABLES)


# ---------------- semantic model
def test_semantic_model_is_valid_yaml():
    import yaml
    from core.config import SEMANTIC_CURATED
    model = yaml.safe_load(SEMANTIC_CURATED.read_text(encoding="utf-8"))
    assert {"tables", "joins", "rules", "metrics"} <= set(model)


# ---------------- answer checker
def test_checker_extra_columns_ok():
    assert is_correct([("SP",)], [("SP", 5067633.16)])


def test_checker_order_and_rounding():
    assert is_correct([(1, 10.001), (2, 20.0)], [(2, 20.0), (1, 10.0)])


def test_checker_wrong_value():
    assert not is_correct([(96096,)], [(99441,)])


# ---------------- failure classifier
def test_classify_customer_ids():
    row = {"gold_sql": "SELECT COUNT(DISTINCT customer_unique_id) FROM customers",
           "ai_sql": "SELECT COUNT(*) FROM customers", "error": ""}
    assert "real customers" in classify(row)


# ---------------- real database
@needs_db
def test_database_has_real_data():
    from core.db import connect
    con = connect()
    assert con.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 99441
    assert con.execute("SELECT COUNT(DISTINCT customer_unique_id) FROM customers").fetchone()[0] == 96096


@needs_db
def test_database_is_read_only():
    import duckdb
    from core.db import connect
    with pytest.raises(duckdb.Error):
        connect().execute("DELETE FROM orders")


@needs_db
def test_all_gold_sql_runs_and_passes_guard():
    from core.db import connect, run_query
    con = connect()
    for q in json.loads(QUESTIONS_FILE.read_text()):
        check_sql(q["gold_sql"], TABLES)
        _, rows = run_query(con, q["gold_sql"])
        assert rows, f"Q{q['id']} returned nothing"
