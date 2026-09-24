"""Accuracy benchmark results: does the semantic layer make the AI more accurate?"""
import json

import altair as alt
import pandas as pd
import streamlit as st

from analyze import classify
from core.config import RESULTS_DIR

MODE_NAMES = {"raw": "Raw (no helper)", "auto": "Auto semantic (AI-written)", "semantic": "Curated semantic"}
MODE_ORDER = ["raw", "auto", "semantic"]
COLORS = {"raw": "#c0504d", "auto": "#e0a030", "semantic": "#2e8b57"}

st.title("Accuracy benchmark")
st.caption("25 real business questions on the Olist data. Each AI answer is run and compared with the correct result.")

summary_path = RESULTS_DIR / "summary.json"
summary = pd.DataFrame(json.loads(summary_path.read_text())) if summary_path.exists() else pd.DataFrame()
if not summary.empty:
    summary = summary[summary["provider"] != "gold"]
if summary.empty:
    st.info("No benchmark results yet. Run:\n\n`python generate_semantic.py --provider groq`\n\n"
            "`python run_benchmark.py --provider groq`")
    st.stop()

summary["run"] = summary["provider"] + " / " + summary["model"]
run = st.selectbox("AI model", sorted(summary["run"].unique()))
s = summary[summary["run"] == run].set_index("mode")

cols = st.columns(4)
for i, m in enumerate(MODE_ORDER):
    if m in s.index:
        cols[i].metric(MODE_NAMES[m], f"{s.loc[m, 'accuracy']:.0f}%")
        cols[i].caption(f"{int(s.loc[m, 'correct'])} of {int(s.loc[m, 'total'])} correct · run {s.loc[m, 'run_at'][:16]}")
if "raw" in s.index and "semantic" in s.index:
    cols[3].metric("Gain from semantic layer", f"{s.loc['semantic', 'accuracy'] - s.loc['raw', 'accuracy']:+.0f} pts")

chart_df = pd.DataFrame([{"mode": m, "Mode": MODE_NAMES[m], "Accuracy": s.loc[m, "accuracy"]}
                         for m in MODE_ORDER if m in s.index])
bars = alt.Chart(chart_df).mark_bar(cornerRadiusEnd=4).encode(
    x=alt.X("Accuracy:Q", scale=alt.Scale(domain=[0, 100]), title="Accuracy (%)"),
    y=alt.Y("Mode:N", sort=[MODE_NAMES[m] for m in MODE_ORDER], title=None),
    color=alt.Color("mode:N", scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values())), legend=None))
st.altair_chart((bars + bars.mark_text(align="left", dx=4).encode(text=alt.Text("Accuracy:Q", format=".0f")))
                .properties(height=170), use_container_width=True)

frames = [pd.read_csv(RESULTS_DIR / f"{s.loc[m, 'label']}.csv").fillna("") for m in s.index
          if (RESULTS_DIR / f"{s.loc[m, 'label']}.csv").exists()]
detail = pd.concat(frames)
detail["correct"] = detail["correct"].astype(str) == "True"

left, right = st.columns([3, 2])
with left:
    st.subheader("Question by question")
    grid = detail.pivot_table(index=["id", "question"], columns="mode", values="correct", aggfunc="first")
    grid = grid[[m for m in MODE_ORDER if m in grid.columns]].rename(columns=MODE_NAMES)
    st.dataframe(grid.replace({True: "✅", False: "❌"}).reset_index(level=0, drop=True),
                 use_container_width=True, height=460)
with right:
    st.subheader("Why the AI was wrong")
    wrong = detail[~detail["correct"]].copy()
    if wrong.empty:
        st.success("No wrong answers!")
    else:
        wrong["category"] = wrong.apply(classify, axis=1)
        cat = wrong.groupby(["category", "mode"]).size().reset_index(name="count")
        st.altair_chart(alt.Chart(cat).mark_bar().encode(
            y=alt.Y("category:N", title=None, sort="-x", axis=alt.Axis(labelLimit=280)),
            x=alt.X("count:Q", title="Wrong answers"),
            color=alt.Color("mode:N", scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values())),
                            legend=alt.Legend(title=None, orient="bottom"))).properties(height=340),
            use_container_width=True)

st.subheader("Inspect a question")
qs = detail[["id", "question"]].drop_duplicates().sort_values("id")
qid = st.selectbox("Question", qs["id"], format_func=lambda i: f"Q{i}: {qs.set_index('id').loc[i, 'question']}")
qrows = detail[detail["id"] == qid].set_index("mode")
st.markdown("**Correct SQL**")
st.code(qrows.iloc[0]["gold_sql"], language="sql")
for m in MODE_ORDER:
    if m in qrows.index:
        r = qrows.loc[m]
        st.markdown(f"**{MODE_NAMES[m]}** {'✅' if r['correct'] else '❌'}")
        st.code(r["ai_sql"] or "(no SQL)", language="sql")
        if r["error"]:
            st.caption(f"Error: {r['error']}")
