"""
Accuracy benchmark on the REAL Olist data.

Asks the AI 25 real business questions in three modes and checks each answer against the correct SQL:
  raw       -> AI sees only table/column names
  auto      -> AI also sees semantic/olist_auto.yaml (written by an AI)
  semantic  -> AI also sees semantic/olist.yaml (written by a data engineer)

Examples:
  python run_benchmark.py --provider gold                 # self-check (must be 100%)
  python run_benchmark.py --provider groq                 # FREE key, all modes
  python run_benchmark.py --provider gemini --mode raw    # one mode
  python run_benchmark.py --provider groq --limit 5       # quick try with 5 questions
"""
import argparse
import csv
import json
import time
from datetime import datetime

from core.agent import allowed_tables, generate_sql
from core.checker import is_correct
from core.config import QUESTIONS_FILE, RESULTS_DIR, SEMANTIC_AUTO
from core.db import connect, run_query
from core.guard import check_sql
from core.llm import DEFAULT_MODELS, PROVIDERS
from core.semantic import build_context


def run_mode(con, questions, mode, provider, model, sleep):
    context = build_context(con, mode)
    tables = allowed_tables(con)
    results, correct = [], 0
    print(f"\n=== Mode: {mode.upper()}  ({provider} {model}) ===", flush=True)
    for q in questions:
        _, gold_rows = run_query(con, q["gold_sql"])
        ai_sql, error, ok = "", "", False
        t0 = time.time()
        try:
            ai_sql = q["gold_sql"] if provider == "gold" else \
                generate_sql(con, q["question"], provider, model, context=context).rstrip(";")
            check_sql(ai_sql, tables)
            _, pred_rows = run_query(con, ai_sql)
            ok = is_correct(gold_rows, pred_rows)
        except Exception as e:  # unsafe/bad SQL, API error, timeout...
            error = str(e).splitlines()[0][:300]
        correct += ok
        print(f"  {'PASS' if ok else 'FAIL'}  Q{q['id']:>2}: {q['question']}", flush=True)
        results.append({"mode": mode, "id": q["id"], "question": q["question"], "correct": ok,
                        "gold_sql": q["gold_sql"], "ai_sql": ai_sql, "error": error,
                        "seconds": round(time.time() - t0, 2)})
        if provider != "gold" and sleep:
            time.sleep(sleep)
    print(f"  -> Accuracy: {correct}/{len(questions)} = {100 * correct / len(questions):.0f}%")
    return results, correct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="gold", choices=["gold"] + PROVIDERS)
    ap.add_argument("--model", default="")
    ap.add_argument("--mode", default="all", choices=["raw", "semantic", "auto", "all"])
    ap.add_argument("--limit", type=int, default=0, help="only the first N questions")
    ap.add_argument("--sleep", type=float, default=0, help="seconds to wait between questions (rate limits)")
    args = ap.parse_args()
    model = args.model or DEFAULT_MODELS.get(args.provider, "gold")

    con = connect()
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    if args.limit:
        questions = questions[:args.limit]
    modes = ["raw", "auto", "semantic"] if args.mode == "all" else [args.mode]
    if "auto" in modes and not SEMANTIC_AUTO.exists():
        print("(skipping auto mode: run  python generate_semantic.py  first)")
        modes.remove("auto")

    RESULTS_DIR.mkdir(exist_ok=True)
    summary_path = RESULTS_DIR / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else []

    for mode in modes:
        start = time.time()
        results, correct = run_mode(con, questions, mode, args.provider, model, args.sleep)
        label = f"{mode}__{args.provider}__{model}".replace("/", "-").replace(":", "-")
        with open(RESULTS_DIR / f"{label}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader()
            w.writerows(results)
        summary = [s for s in summary if s["label"] != label]
        summary.append({"label": label, "mode": mode, "provider": args.provider, "model": model,
                        "correct": correct, "total": len(questions),
                        "accuracy": round(100 * correct / len(questions), 1),
                        "seconds": round(time.time() - start, 1),
                        "run_at": datetime.now().isoformat(timespec="seconds")})
    summary_path.write_text(json.dumps(summary, indent=2))

    print("\nSummary:")
    for s in summary:
        if s["provider"] == args.provider and s["model"] == model:
            print(f"  {s['mode']:<9} {s['correct']:>2}/{s['total']}  {s['accuracy']:>5}%")
    print("Next: python analyze.py   |   streamlit run app.py")


if __name__ == "__main__":
    main()
