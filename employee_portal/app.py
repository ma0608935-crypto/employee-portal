"""
Employee Performance & Management Portal
Main application entry point
"""

import streamlit as st
import os
from modules.auth import login_page, logout
from modules.database import init_db
from modules.workspace import render_workspace

# ─────────────────────────────────────────────
# Page Config  (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Employee Portal",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Reset & Fonts ─────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #0F1117 !important;
    color: #E8EAF0 !important;
    font-family: 'Inter', sans-serif !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="collapsedControl"],
section[data-testid="stSidebar"] {
    display: none !important;
}

/* ── Scrollbar ──────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #1A1D27; }
::-webkit-scrollbar-thumb { background: #3B4063; border-radius: 3px; }

/* ── Buttons ────────────────────────────────── */
div.stButton > button {
    background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.55rem 1.4rem !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    letter-spacing: 0.02em !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 12px rgba(79,107,255,0.35) !important;
}
div.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 18px rgba(79,107,255,0.5) !important;
}

/* ── Inputs ─────────────────────────────────── */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stSelectbox"] div[data-baseweb="select"],
div[data-testid="stDateInput"] input,
div[data-testid="stTimeInput"] input {
    background: #1A1D27 !important;
    border: 1px solid #2E3350 !important;
    border-radius: 10px !important;
    color: #E8EAF0 !important;
    font-family: 'Inter', sans-serif !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: #4F6BFF !important;
    box-shadow: 0 0 0 2px rgba(79,107,255,0.2) !important;
}

/* ── Tabs ───────────────────────────────────── */
div[data-testid="stTabs"] > div > div[role="tablist"] {
    background: #1A1D27 !important;
    border-radius: 14px !important;
    padding: 6px !important;
    gap: 4px !important;
    border: 1px solid #2E3350 !important;
}
div[data-testid="stTabs"] button[role="tab"] {
    border-radius: 10px !important;
    padding: 0.5rem 1.25rem !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    color: #8B90A8 !important;
    border: none !important;
    transition: all 0.2s !important;
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%) !important;
    color: white !important;
    box-shadow: 0 2px 12px rgba(79,107,255,0.4) !important;
}
div[data-testid="stTabs"] div[role="tabpanel"] {
    background: transparent !important;
    border: none !important;
    padding-top: 1rem !important;
}

/* ── Metric Cards ───────────────────────────── */
div[data-testid="stMetric"] {
    background: #1A1D27 !important;
    border: 1px solid #2E3350 !important;
    border-radius: 14px !important;
    padding: 1.2rem !important;
}
div[data-testid="stMetric"] label {
    color: #8B90A8 !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #E8EAF0 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.75rem !important;
}
div[data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
}

/* ── DataFrames ─────────────────────────────── */
div[data-testid="stDataFrame"] > div {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid #2E3350 !important;
}

/* ── Dividers ───────────────────────────────── */
hr { border-color: #2E3350 !important; margin: 1rem 0 !important; }

/* ── Alerts ─────────────────────────────────── */
div[data-testid="stAlert"] {
    border-radius: 10px !important;
    border: none !important;
}

/* ── Expander ───────────────────────────────── */
div[data-testid="stExpander"] {
    background: #1A1D27 !important;
    border: 1px solid #2E3350 !important;
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────
init_db()

# ─────────────────────────────────────────────
# Routing
# ─────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
else:
    render_workspace()
