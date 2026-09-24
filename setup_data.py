"""
Download the REAL Olist e-commerce dataset and load it into DuckDB.

Olist is a real Brazilian marketplace. The data is ~100,000 real (anonymised) orders
from 2016-2018. License: CC BY-NC-SA 4.0 (https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

Run:  python setup_data.py            (downloads ~65 MB once, then builds data/olist.duckdb)
      python setup_data.py --force    (rebuild)
"""
import argparse
import sys
import urllib.request

import duckdb

from core.config import DB_PATH, RAW_DIR

MIRROR = "https://raw.githubusercontent.com/spdrio/Brazilian-E-Commerce-Public-Dataset-by-Olist/master/files/"

# table name -> (csv file, column types we want to enforce)
TABLES = {
    "customers": ("olist_customers_dataset.csv", {"customer_zip_code_prefix": "VARCHAR"}),
    "sellers": ("olist_sellers_dataset.csv", {"seller_zip_code_prefix": "VARCHAR"}),
    "products": ("olist_products_dataset.csv", {}),
    "orders": ("olist_orders_dataset.csv", {
        "order_purchase_timestamp": "TIMESTAMP", "order_approved_at": "TIMESTAMP",
        "order_delivered_carrier_date": "TIMESTAMP", "order_delivered_customer_date": "TIMESTAMP",
        "order_estimated_delivery_date": "TIMESTAMP"}),
    "order_items": ("olist_order_items_dataset.csv", {
        "shipping_limit_date": "TIMESTAMP", "price": "DECIMAL(12,2)", "freight_value": "DECIMAL(12,2)"}),
    "order_payments": ("olist_order_payments_dataset.csv", {"payment_value": "DECIMAL(12,2)"}),
    "order_reviews": ("olist_order_reviews_dataset.csv", {
        "review_creation_date": "TIMESTAMP", "review_answer_timestamp": "TIMESTAMP"}),
    "category_translation": ("product_category_name_translation.csv", {}),
}


def download(force=False):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for _, (fname, _) in TABLES.items():
        dest = RAW_DIR / fname
        if dest.exists() and not force:
            continue
        print(f"  downloading {fname} ...", flush=True)
        urllib.request.urlretrieve(MIRROR + fname, dest)


def build(force=False):
    if DB_PATH.exists():
        if not force:
            print(f"{DB_PATH} already exists (use --force to rebuild)")
            return
        DB_PATH.unlink()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = DB_PATH.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = duckdb.connect(str(tmp))
    for table, (fname, types) in TABLES.items():
        path = str(RAW_DIR / fname).replace("'", "''")
        type_arg = ", types = {" + ", ".join(f"'{c}': '{t}'" for c, t in types.items()) + "}" if types else ""
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv('{path}', header = true{type_arg})")
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<22} {n:>8,} rows")
    con.close()
    tmp.rename(DB_PATH)
    print(f"Done: {DB_PATH}")


def ensure_database():
    """Used by the app: build the database on first start if it is missing."""
    if not DB_PATH.exists():
        download()
        build()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    try:
        download(args.force)
        build(args.force)
    except Exception as e:  # network problems etc.
        sys.exit(f"Failed: {e}")
