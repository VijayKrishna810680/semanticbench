"""Compare the AI's query result with the correct result."""
from decimal import Decimal


def norm(v):
    """Make values comparable: round numbers to 2 decimals, lower-case text."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float, Decimal)):
        return round(float(v), 2)
    return str(v).strip().lower()


def is_correct(gold_rows, pred_rows) -> bool:
    """
    Correct if every column of the correct answer also appears in the AI's answer
    with the same values (any row order). Extra columns from the AI are allowed.
    """
    if len(gold_rows) != len(pred_rows):
        return False
    if not gold_rows:
        return True
    pred_cols = [sorted(map(norm, col), key=str) for col in zip(*pred_rows)]
    return all(sorted(map(norm, g), key=str) in pred_cols for g in zip(*gold_rows))
