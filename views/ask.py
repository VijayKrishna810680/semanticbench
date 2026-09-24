"""Ask questions about REAL e-commerce data in plain English."""
import streamlit as st

from core.agent import answer_question
from core.logs import log_answer, save_feedback
from core.ui import auto_chart, get_cursor, sidebar_settings, to_dataframe


provider, model, api_key, ready = sidebar_settings()
st.sidebar.header("Options")
compare = st.sidebar.toggle("Compare with AI without semantic layer", value=False,
                            help="Runs the same question with only raw table names, side by side")
summarize = st.sidebar.toggle("Plain-English answer", value=True)

st.title("Ask your data")
st.caption("Real data: ~100,000 orders from the Olist marketplace in Brazil (Sep 2016 - Oct 2018). "
           "The AI uses a **semantic layer** to understand what the data means, writes SQL, "
           "and runs it **read-only**.")

EXAMPLES = [
    "What was our total revenue in 2018?",
    "Top 10 product categories by revenue",
    "Monthly number of delivered orders in 2017",
    "Which states have the highest late delivery rate?",
    "How many repeat customers do we have?",
    "Average review score by payment type",
]
cols = st.columns(3)
for i, ex in enumerate(EXAMPLES):
    if cols[i % 3].button(ex, use_container_width=True):
        st.session_state["pending"] = ex

if "history" not in st.session_state:
    st.session_state["history"] = []


def show_answer(ans, title=None, key=""):
    if title:
        st.markdown(f"**{title}**")
    if not ans.ok:
        st.error(ans.error)
    else:
        if ans.summary:
            st.markdown(ans.summary)
        df = to_dataframe(ans.columns, ans.rows)
        auto_chart(df)
        st.dataframe(df, use_container_width=True, hide_index=True)
    with st.expander(f"SQL · {ans.seconds}s · {ans.attempts} attempt(s)"):
        st.code(ans.sql or "(no SQL)", language="sql")


def render(item, idx):
    with st.chat_message("user"):
        st.write(item["question"])
    with st.chat_message("assistant"):
        if item.get("raw"):
            left, right = st.columns(2)
            with left:
                show_answer(item["main"], "With semantic layer")
            with right:
                show_answer(item["raw"], "Without semantic layer (raw tables only)")
        else:
            show_answer(item["main"])
        fb = st.feedback("thumbs", key=f"fb_{idx}")
        if fb is not None and item.get("log_id") and item.get("fb") != fb:
            save_feedback(item["log_id"], "up" if fb == 1 else "down")
            item["fb"] = fb


for idx, item in enumerate(st.session_state["history"]):
    render(item, idx)

question = st.chat_input("Ask a business question, e.g. 'Revenue by state in 2018'",
                         disabled=not ready) or st.session_state.pop("pending", None)
if question:
    if not ready:
        st.warning("Add a free API key in the sidebar first.")
        st.stop()
    with st.spinner("Thinking, writing SQL and running it..."):
        main = answer_question(get_cursor(), question, provider, model, mode="semantic",
                               summarize=summarize, api_key=api_key)
        raw = answer_question(get_cursor(), question, provider, model, mode="raw",
                              summarize=summarize, api_key=api_key) if compare else None
    item = {"question": question, "main": main, "raw": raw,
            "log_id": log_answer(main, provider, model)}
    st.session_state["history"].append(item)
    render(item, len(st.session_state["history"]) - 1)

if not ready:
    st.info("To start: get a **free** key at console.groq.com (no credit card) and paste it in the sidebar. "
            "Or set GROQ_API_KEY before starting the app.")
