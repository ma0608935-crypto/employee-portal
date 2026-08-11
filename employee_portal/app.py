"""
Employee Performance & Management Portal
Main application entry point
"""

import streamlit as st
import os
from modules.auth import login_page, logout
from modules.database import init_db
from modules.workspace import render_workspace

# ─────────────────────────────────────────────────────────────
# Page Config  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Employee Portal",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# Initialize Dark/Light Mode
# ─────────────────────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True  # Default: Dark mode


def get_theme_css():
    """Return CSS based on current theme."""
    if st.session_state.dark_mode:
        return """
        <style>
        /* ── Dark Mode ─────────────────────────── */
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
        div[data-testid="stTimeInput"] input,
        div[data-testid="stNumberInput"] input {
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
        div[data-testid="stSelectbox"] div[data-baseweb="select"] div {
            color: #E8EAF0 !important;
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
            color: #8B90A8 !important;
        }

        /* ── DataFrames ─────────────────────────────── */
        div[data-testid="stDataFrame"] > div {
            border-radius: 12px !important;
            overflow: hidden !important;
            border: 1px solid #2E3350 !important;
        }
        div[data-testid="stDataFrame"] table {
            color: #E8EAF0 !important;
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
        div[data-testid="stExpander"] summary {
            color: #E8EAF0 !important;
        }

        /* ── Radio buttons ──────────────────────────── */
        div[data-testid="stRadio"] label {
            color: #8B90A8 !important;
        }
        div[data-testid="stRadio"] label[data-selected="true"] {
            color: #E8EAF0 !important;
        }

        /* ── Selectbox dropdown ─────────────────────── */
        div[data-baseweb="select"] ul {
            background: #1A1D27 !important;
            border: 1px solid #2E3350 !important;
        }
        div[data-baseweb="select"] ul li {
            color: #E8EAF0 !important;
        }
        div[data-baseweb="select"] ul li:hover {
            background: #2E3350 !important;
        }

        /* ── Toggle Switch ──────────────────────────── */
        .theme-toggle {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0.3rem 0;
        }
        .theme-toggle-label {
            color: #8B90A8;
            font-size: 0.8rem;
            font-weight: 500;
        }

        /* ── StAlert text ───────────────────────────── */
        div[data-testid="stAlert"] div {
            color: #E8EAF0 !important;
        }
        </style>
        """
    else:
        return """
        <style>
        /* ── Light Mode ─────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

        html, body, [data-testid="stAppViewContainer"] {
            background: #F0F2F6 !important;
            color: #1A1D27 !important;
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
        ::-webkit-scrollbar-track { background: #E8EAF0; }
        ::-webkit-scrollbar-thumb { background: #B0B8D0; border-radius: 3px; }

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
        /* Secondary buttons (like theme toggle) */
        div.stButton > button[kind="secondary"] {
            background: #FFFFFF !important;
            color: #1A1D27 !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1) !important;
            border: 1px solid #D0D5E0 !important;
        }
        div.stButton > button[kind="secondary"]:hover {
            background: #F0F2F6 !important;
        }

        /* ── Inputs ─────────────────────────────────── */
        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stSelectbox"] div[data-baseweb="select"],
        div[data-testid="stDateInput"] input,
        div[data-testid="stTimeInput"] input,
        div[data-testid="stNumberInput"] input {
            background: #FFFFFF !important;
            border: 1px solid #D0D5E0 !important;
            border-radius: 10px !important;
            color: #1A1D27 !important;
            font-family: 'Inter', sans-serif !important;
        }
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stTextArea"] textarea:focus {
            border-color: #4F6BFF !important;
            box-shadow: 0 0 0 2px rgba(79,107,255,0.2) !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] div {
            color: #1A1D27 !important;
        }

        /* ── Tabs ───────────────────────────────────── */
        div[data-testid="stTabs"] > div > div[role="tablist"] {
            background: #FFFFFF !important;
            border-radius: 14px !important;
            padding: 6px !important;
            gap: 4px !important;
            border: 1px solid #D0D5E0 !important;
        }
        div[data-testid="stTabs"] button[role="tab"] {
            border-radius: 10px !important;
            padding: 0.5rem 1.25rem !important;
            font-weight: 500 !important;
            font-size: 0.875rem !important;
            color: #6B7280 !important;
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
            background: #FFFFFF !important;
            border: 1px solid #D0D5E0 !important;
            border-radius: 14px !important;
            padding: 1.2rem !important;
        }
        div[data-testid="stMetric"] label {
            color: #6B7280 !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.06em !important;
        }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            color: #1A1D27 !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 700 !important;
            font-size: 1.75rem !important;
        }
        div[data-testid="stMetricDelta"] {
            font-size: 0.8rem !important;
            color: #6B7280 !important;
        }

        /* ── DataFrames ─────────────────────────────── */
        div[data-testid="stDataFrame"] > div {
            border-radius: 12px !important;
            overflow: hidden !important;
            border: 1px solid #D0D5E0 !important;
        }
        div[data-testid="stDataFrame"] table {
            color: #1A1D27 !important;
        }
        div[data-testid="stDataFrame"] thead th {
            background: #F0F2F6 !important;
            color: #1A1D27 !important;
        }
        div[data-testid="stDataFrame"] tbody td {
            background: #FFFFFF !important;
            color: #1A1D27 !important;
        }

        /* ── Dividers ───────────────────────────────── */
        hr { border-color: #D0D5E0 !important; margin: 1rem 0 !important; }

        /* ── Alerts ─────────────────────────────────── */
        div[data-testid="stAlert"] {
            border-radius: 10px !important;
            border: none !important;
        }
        div[data-testid="stAlert"] div {
            color: #1A1D27 !important;
        }

        /* ── Expander ───────────────────────────────── */
        div[data-testid="stExpander"] {
            background: #FFFFFF !important;
            border: 1px solid #D0D5E0 !important;
            border-radius: 12px !important;
        }
        div[data-testid="stExpander"] summary {
            color: #1A1D27 !important;
        }
        div[data-testid="stExpander"] div {
            color: #1A1D27 !important;
        }

        /* ── Radio buttons ──────────────────────────── */
        div[data-testid="stRadio"] label {
            color: #6B7280 !important;
        }
        div[data-testid="stRadio"] label[data-selected="true"] {
            color: #1A1D27 !important;
        }

        /* ── Selectbox dropdown ─────────────────────── */
        div[data-baseweb="select"] ul {
            background: #FFFFFF !important;
            border: 1px solid #D0D5E0 !important;
        }
        div[data-baseweb="select"] ul li {
            color: #1A1D27 !important;
        }
        div[data-baseweb="select"] ul li:hover {
            background: #F0F2F6 !important;
        }

        /* ── Toggle Switch ──────────────────────────── */
        .theme-toggle {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0.3rem 0;
        }
        .theme-toggle-label {
            color: #6B7280;
            font-size: 0.8rem;
            font-weight: 500;
        }

        /* ── Image / Logo ───────────────────────────── */
        .avatar-wrapper .avatar-initials {
            background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%) !important;
            color: white !important;
        }

        /* ── Card backgrounds ───────────────────────── */
        .cb-card, .pcard, .notes-panel, .att-card, .break-card, .email-card, .report-card {
            background: #FFFFFF !important;
            border-color: #D0D5E0 !important;
        }
        .cb-card .cb-name, .pcard .pcard-name, .notes-panel .notes-title {
            color: #1A1D27 !important;
        }
        .cb-card .cb-detail, .pcard .pcard-detail, .notes-panel .note-text {
            color: #4A4A6A !important;
        }
        .cb-card .cb-phone, .pcard .pcard-label {
            color: #6B7280 !important;
        }
        .note-item {
            background: #F0F2F6 !important;
            border-color: #D0D5E0 !important;
        }
        .no-notes {
            color: #6B7280 !important;
        }
        .cb-notes {
            border-color: #D0D5E0 !important;
            color: #6B7280 !important;
        }
        .checkin-status.checked {
            background: #E8F5E9 !important;
            border-color: #06D6A055 !important;
        }
        .checkin-status.late {
            background: #FFF3E0 !important;
            border-color: #FFD16655 !important;
        }
        .checkin-status.checked div,
        .checkin-status.late div {
            color: #1A1D27 !important;
        }

        /* ── Break cards ────────────────────────────── */
        .break-card {
            background: #FFFFFF !important;
            border-color: #D0D5E0 !important;
        }
        .break-card .break-name {
            color: #1A1D27 !important;
        }
        .break-card .break-time {
            color: #6B7280 !important;
        }
        .break-card.break-active {
            background: #E3E8FF !important;
            border-color: #4F6BFF !important;
        }
        .break-card.break-done {
            background: #E8F5E9 !important;
            border-color: #06D6A055 !important;
        }

        /* ── Status pills ───────────────────────────── */
        .status-pill {
            color: #1A1D27 !important;
        }
        .status-pill.status-cold {
            background: #E3E8FF !important;
            color: #4F6BFF !important;
        }
        .status-pill.status-warm {
            background: #FFF3E0 !important;
            color: #FF9F43 !important;
        }
        .status-pill.status-hot {
            background: #FFEBEE !important;
            color: #FF6B6B !important;
        }
        .status-pill.status-pending {
            background: #FFF8E1 !important;
            color: #FFD166 !important;
        }
        .status-pill.status-completed {
            background: #E8F5E9 !important;
            color: #06D6A0 !important;
        }
        .status-pill.status-cancelled {
            background: #FFEBEE !important;
            color: #FF6B6B !important;
        }
        </style>
        """


# ─────────────────────────────────────────────────────────────
# Global CSS (Dynamic based on theme)
# ─────────────────────────────────────────────────────────────
st.markdown(get_theme_css(), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────────────────────
init_db()

# ─────────────────────────────────────────────────────────────
# Routing
# ─────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
else:
    render_workspace()
