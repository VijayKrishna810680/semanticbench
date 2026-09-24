"""Monitoring: every live question, its SQL, success, speed and user feedback."""
import pandas as pd
import streamlit as st

from core.logs import read_log

st.title("Query log")
st.caption("Every question asked in the app. Use failures and thumbs-down answers to improve the semantic model.")

log = pd.DataFrame(read_log())
if log.empty:
    st.info("No questions asked yet.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Questions", len(log))
c2.metric("Success rate", f"{100 * log['ok'].mean():.0f}%")
c3.metric("Avg response time", f"{log['seconds'].mean():.1f}s")
fb = log["feedback"].value_counts()
c4.metric("Feedback 👍 / 👎", f"{fb.get('up', 0)} / {fb.get('down', 0)}")

only_bad = st.toggle("Show only failures and 👎")
view = log[(log["ok"] == 0) | (log["feedback"] == "down")] if only_bad else log
st.dataframe(view[["ts", "question", "ok", "rows", "seconds", "attempts", "feedback", "error", "sql", "model"]],
             use_container_width=True, hide_index=True)
st.download_button("Download log (CSV)", log.to_csv(index=False), "query_log.csv", "text/csv")
