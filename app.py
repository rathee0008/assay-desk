from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Assay — Metals & Macro Intelligence Desk",
    page_icon="🪙",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container { padding: 0 !important; max-width: 100% !important; }
      header[data-testid="stHeader"] { display: none; }
      iframe { border: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

dashboard_path = Path(__file__).parent / "dashboard.html"
st.iframe(src=dashboard_path, height=1400, width="stretch")
