"""Show the semantic models and the raw database schema."""
import streamlit as st

from core.config import SEMANTIC_AUTO, SEMANTIC_CURATED
from core.db import raw_schema
from core.ui import get_cursor

st.title("Semantic model")
st.caption("The semantic layer is the 'dictionary' that tells the AI what the data means and how the business measures it.")

tab1, tab2, tab3 = st.tabs(["Curated (by a data engineer)", "Auto-generated (by AI)", "Raw schema (what AI sees without help)"])
with tab1:
    st.code(SEMANTIC_CURATED.read_text(encoding="utf-8"), language="yaml")
with tab2:
    if SEMANTIC_AUTO.exists():
        st.code(SEMANTIC_AUTO.read_text(encoding="utf-8"), language="yaml")
    else:
        st.info("Not generated yet. Run `python generate_semantic.py --provider groq`.")
with tab3:
    st.code(raw_schema(get_cursor()), language="sql")
