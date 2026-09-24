"""Shared Streamlit helpers (database connection, API keys, sidebar settings)."""
import os

import pandas as pd
import streamlit as st

from core.db import connect
from core.llm import DEFAULT_MODELS, KEY_ENV, PROVIDERS, has_key

KEY_NAMES = [k for k in set(KEY_ENV.values()) if k]


def load_secrets():
    """Copy API keys from Streamlit secrets (cloud deployment) into environment variables."""
    try:
        for k in KEY_NAMES + ["SB_PROVIDER", "SB_MODEL"]:
            if k in st.secrets and not os.getenv(k):
                os.environ[k] = str(st.secrets[k])
    except Exception:  # no secrets file locally -> fine
        pass


@st.cache_resource(show_spinner="Preparing the real Olist database (first start only, ~30s)...")
def _shared_connection():
    from setup_data import ensure_database
    ensure_database()
    return connect()


def get_cursor():
    """A separate cursor per use -- safe with Streamlit's threads."""
    return _shared_connection().cursor()


def sidebar_settings():
    load_secrets()
    st.sidebar.header("AI settings")
    default = os.getenv("SB_PROVIDER", "groq")
    provider = st.sidebar.selectbox("Provider", PROVIDERS, index=PROVIDERS.index(default) if default in PROVIDERS else 0,
                                    help="groq, gemini and ollama are free")
    env = KEY_ENV.get(provider)
    api_key = ""
    if env and not has_key(provider):
        api_key = st.sidebar.text_input(f"{env}", type="password", key=f"key_{provider}",
                                        help="Kept only in your browser session. Never stored or logged.")
    model = st.sidebar.text_input("Model", value=os.getenv("SB_MODEL") or DEFAULT_MODELS[provider])
    ready = has_key(provider, api_key)
    st.sidebar.caption("✅ AI ready" if ready else "⚠️ Add a free API key to ask questions")
    return provider, model, api_key, ready


def to_dataframe(columns, rows) -> pd.DataFrame:
    """Build a table; turn exact decimals (money) into normal numbers so charts work."""
    from decimal import Decimal
    df = pd.DataFrame(rows, columns=columns)
    for c in df.columns:
        if df[c].map(lambda v: isinstance(v, Decimal)).any():
            df[c] = df[c].astype(float)
    return df


def auto_chart(df: pd.DataFrame):
    """Draw a simple chart when the result is a label + number table."""
    import altair as alt
    if df.shape[1] < 2 or not (2 <= len(df) <= 60):
        return
    label, value = df.columns[0], df.columns[-1]
    if not pd.api.types.is_numeric_dtype(df[value]) or label == value:
        return
    data = df[[label, value]].copy()
    data.columns = ["label", "value"]  # safe field names for the chart
    name = str(label).lower()
    if any(k in name for k in ("month", "date", "year", "week", "day", "period")):
        chart = alt.Chart(data).mark_line(point=True).encode(
            x=alt.X("label:O", title=str(label)), y=alt.Y("value:Q", title=str(value)))
    else:
        chart = alt.Chart(data).mark_bar().encode(
            y=alt.Y("label:N", sort="-x", title=None), x=alt.X("value:Q", title=str(value)),
            tooltip=["label", "value"])
    st.altair_chart(chart.properties(height=min(40 + 24 * len(data), 420)), use_container_width=True)
