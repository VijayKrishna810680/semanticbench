"""
The live question-answering agent.

question -> AI writes SQL (using the semantic model) -> safety check -> run read-only
         -> if it fails, AI gets the error and fixes the SQL (1 retry) -> short answer in plain English
"""
import time
from dataclasses import dataclass, field

from core.config import MAX_ROWS
from core.db import run_query
from core.guard import UnsafeSQLError, check_sql
from core.llm import ask_llm, extract_block
from core.semantic import FIX_PROMPT, SQL_PROMPT, SUMMARY_PROMPT, build_context


@dataclass
class Answer:
    question: str
    sql: str = ""
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    summary: str = ""
    error: str = ""
    attempts: int = 0
    seconds: float = 0.0

    @property
    def ok(self):
        return not self.error


def allowed_tables(con):
    return {r[0].lower() for r in con.execute("SHOW TABLES").fetchall()}


def generate_sql(con, question, provider, model, mode="semantic", context=None):
    """Only the SQL-writing step (used by the benchmark)."""
    context = context or build_context(con, mode)
    return extract_block(ask_llm(provider, model, SQL_PROMPT.format(context=context, question=question)))


def answer_question(con, question, provider, model, mode="semantic", summarize=True, max_fixes=1, api_key=""):
    start = time.time()
    ans = Answer(question=question)
    tables = allowed_tables(con)
    messages = [{"role": "user", "content": SQL_PROMPT.format(
        context=build_context(con, mode), question=question)}]
    try:
        for attempt in range(max_fixes + 1):
            ans.attempts = attempt + 1
            reply = ask_llm(provider, model, messages=messages, api_key=api_key)
            ans.sql = extract_block(reply).rstrip(";")
            try:
                check_sql(ans.sql, tables)
                ans.columns, ans.rows = run_query(con, ans.sql, max_rows=MAX_ROWS)
                ans.error = ""
                break
            except UnsafeSQLError as e:  # never retry around the safety check
                ans.error = f"Blocked for safety: {e}"
                break
            except Exception as e:
                ans.error = str(e).splitlines()[0][:300]
                messages += [{"role": "assistant", "content": reply},
                             {"role": "user", "content": FIX_PROMPT.format(error=ans.error)}]
        if ans.ok and summarize:
            preview = [dict(zip(ans.columns, r)) for r in ans.rows[:15]]
            ans.summary = ask_llm(provider, model, SUMMARY_PROMPT.format(
                question=question, rows=preview), max_tokens=600, api_key=api_key).strip()
    except Exception as e:  # AI provider problems (no key, network...)
        ans.error = str(e).splitlines()[0][:300]
    ans.seconds = round(time.time() - start, 2)
    return ans
