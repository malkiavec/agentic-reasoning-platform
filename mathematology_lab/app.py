"""Run with: streamlit run mathematology_lab/app.py"""
import os
import streamlit as st
from mathematology_lab.core import connect, import_snapshot, list_draws

st.set_page_config(page_title="Mathematology Lab", page_icon="🧪", layout="wide")
st.title("Mathematology Lab")
st.caption("Single-user mathematical research workstation · Data Foundation v0.1")
db_path = os.getenv("MATHEMATOLOGY_DB", "mathematology_lab.sqlite3")
db = connect(db_path)
st.subheader("Historical NY Lotto snapshots")
st.write("Upload a CSV with draw_date (YYYY-MM-DD), winning_numbers (six space-separated numbers), and optional bonus.")
upload = st.file_uploader("Import historical draws", type=["csv"])
if upload is not None and st.button("Validate and import snapshot"):
    try:
        snapshot = import_snapshot(db, upload.getvalue().decode("utf-8-sig"), upload.name)
        st.success(f"Imported immutable snapshot: {snapshot[:16]}…")
    except (ValueError, UnicodeDecodeError) as error:
        st.error(str(error))
snapshots = db.execute("SELECT id,source,row_count FROM snapshots ORDER BY imported_at DESC,id").fetchall()
if snapshots:
    selected = st.selectbox("Dataset snapshot", snapshots, format_func=lambda x: f"{x[1]} · {x[2]} draws · {x[0][:12]}")
    draws = list_draws(db, selected[0])
    st.metric("Validated draws", len(draws))
    st.dataframe(draws[::-1], use_container_width=True)
    st.download_button("Export selected snapshot (JSON)", __import__("json").dumps(draws, indent=2),
                       file_name=f"snapshot-{selected[0][:12]}.json", mime="application/json")
else:
    st.info("Import your first CSV to initialize the research history.")
st.divider()
st.subheader("Research engines")
st.info("PythonPlayground, Readingtext and Lotto Markov Model are planned adapters. No model code has been changed or connected yet.")
st.subheader("AI research assistant")
st.caption("Planned: optional OpenAI API integration with evidence-linked explanations. No key is required for v0.1.")
