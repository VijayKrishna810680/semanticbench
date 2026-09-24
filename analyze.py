"""
Error analysis: WHY did the AI get questions wrong?
Reads results/*.csv, puts each wrong answer into a category, saves results/failure_analysis.csv.

  python analyze.py
"""
import csv
import re
from collections import Counter, defaultdict

from core.config import RESULTS_DIR

CATEGORIES = [
    "SQL error / blocked / timeout",
    "Counted order-level IDs instead of real customers",
    "Missing 'delivered' status filter",
    "Wrong revenue definition (payments or freight)",
    "Portuguese category names (no translation)",
    "Wrong date or delivery logic",
    "Other logic error",
]


def classify(row) -> str:
    gold = row["gold_sql"].lower()
    ai = (row["ai_sql"] or "").lower()
    if row["error"]:
        return CATEGORIES[0]
    if "customer_unique_id" in gold and "customer_unique_id" not in ai:
        return CATEGORIES[1]
    if "'delivered'" in gold and "'delivered'" not in ai:
        return CATEGORIES[2]
    if "sum(oi.price)" in gold and ("payment_value" in ai or "freight_value" in ai):
        return CATEGORIES[3]
    if "category_translation" in gold and "category_translation" not in ai:
        return CATEGORIES[4]
    if re.search(r"cast\(|date_diff|year\(|month\(|strftime", gold):
        return CATEGORIES[5]
    return CATEGORIES[6]


def main():
    files = sorted(f for f in RESULTS_DIR.glob("*.csv") if f.name != "failure_analysis.csv")
    if not files:
        raise SystemExit("No results yet. Run run_benchmark.py first.")
    out, by_run = [], defaultdict(Counter)
    for f in files:
        for row in csv.DictReader(open(f, encoding="utf-8")):
            if row["correct"] == "True":
                continue
            cat = classify(row)
            by_run[f.stem][cat] += 1
            out.append({"run": f.stem, "id": row["id"], "question": row["question"],
                        "category": cat, "ai_sql": row["ai_sql"], "error": row["error"]})
    with open(RESULTS_DIR / "failure_analysis.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["run", "id", "question", "category", "ai_sql", "error"])
        w.writeheader()
        w.writerows(out)
    for run, counts in by_run.items():
        print(f"\n{run}: {sum(counts.values())} wrong")
        for cat, n in counts.most_common():
            print(f"  {n:>3}  {cat}")
    if not by_run:
        print("No wrong answers found.")
    print("\nSaved results/failure_analysis.csv")


if __name__ == "__main__":
    main()
