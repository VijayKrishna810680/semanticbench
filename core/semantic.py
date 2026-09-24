"""Build the context the AI sees: raw schema only, or schema + a semantic model."""
from core.config import SEMANTIC_AUTO, SEMANTIC_CURATED
from core.db import raw_schema

MODES = {"raw": None, "semantic": SEMANTIC_CURATED, "auto": SEMANTIC_AUTO}


def build_context(con, mode: str = "semantic") -> str:
    schema = raw_schema(con)
    path = MODES[mode]
    if path is None:
        return f"Database schema:\n{schema}"
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found. Run: python generate_semantic.py")
    return (f"Database schema:\n{schema}\n\n"
            "Semantic model (business meaning of the data -- follow these definitions exactly):\n"
            + path.read_text(encoding="utf-8"))


SQL_PROMPT = """You are a senior data analyst. Write ONE DuckDB SQL SELECT query that answers the question.

{context}

Question: {question}

Return only the SQL inside a ```sql code block. No explanation."""

FIX_PROMPT = """That query failed with this error:
{error}

Fix it. Return only the corrected SQL inside a ```sql code block."""

SUMMARY_PROMPT = """Question: {question}
SQL result (first rows): {rows}

Answer the question in one or two short sentences for a business user, using the numbers above.
Format money as BRL with thousands separators. Do not mention SQL."""
