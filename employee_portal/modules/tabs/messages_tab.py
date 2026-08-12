"""
modules/tabs/messages_tab.py
Internal messaging system (simple version without email)
"""

import streamlit as st
from datetime import datetime


def render_messages_tab(user: dict):
    """Render the messages tab."""
    st.markdown("""
    <style>
    .msg-card {
        background: #1A1D27;
        border: 1px solid #2E3350;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
    }
    .msg-title {
        font-weight: 600;
        color: #E8EAF0;
        font-size: 1rem;
    }
    .msg-sub {
        color: #8B90A8;
        font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="msg-card">
        <div class="msg-title">📧 Messages</div>
        <div class="msg-sub">
            This feature is currently unavailable.
            <br>Please contact your administrator for assistance.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("ℹ️ Messaging feature is disabled. Admin will enable it soon.")
