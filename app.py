"""
SemanticBench - ask questions about REAL e-commerce data, and measure AI accuracy.
Run:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="SemanticBench", page_icon="📊", layout="wide")

nav = st.navigation([
    st.Page("views/ask.py", title="Ask your data", icon="💬", default=True),
    st.Page("views/benchmark.py", title="Accuracy benchmark", icon="📊"),
    st.Page("views/semantic_model.py", title="Semantic model", icon="📖"),
    st.Page("views/query_log.py", title="Query log", icon="🧾"),
])
nav.run()
