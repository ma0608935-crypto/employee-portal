"""
modules/workspace.py
"""

import streamlit as st
from modules.auth import logout
from modules.database import get_user
from modules.tabs.profile_tab import render_profile_tab
from modules.tabs.sales_tab import render_sales_tab
from modules.tabs.attendance_tab import render_attendance_tab
from modules.tabs.breaks_tab import render_breaks_tab
from modules.tabs.callbacks_tab import render_callbacks_tab
from modules.tabs.admin_tab import render_admin_tab
from modules.tabs.maps_tab import render_maps_tab
from modules.tabs.reports_tab import render_reports_tab  # ✅ جديد
from modules.components import profile_card, notes_panel, performance_dashboard
from datetime import datetime


def render_workspace():
    user = st.session_state.user
    fresh = get_user(user["username"])
    if fresh:
        st.session_state.user = fresh
        user = fresh

    _render_topbar(user)
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    col_profile, col_notes = st.columns([2, 1], gap="medium")
    with col_profile:
        profile_card(user)
    with col_notes:
        notes_panel(user)

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
    performance_dashboard(user)
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown('<hr style="border-color:#2E3350;margin:0">', unsafe_allow_html=True)
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    is_admin = user["role"] in ("admin", "leader")

    if is_admin:
        tab_labels = ["👤 Profile", "💰 Sales", "📋 Attendance", "☕ Breaks", "📞 Callbacks", "🗺️ Maps", "📊 Reports", "🛡️ Admin"]
    else:
        tab_labels = ["👤 Profile", "💰 Sales", "📋 Attendance", "☕ Breaks", "📞 Callbacks", "🗺️ Maps", "📊 Reports"]

    selected_tab = st.radio(
        "Navigation",
        tab_labels,
        horizontal=True,
        label_visibility="collapsed",
        key="main_nav_radio"
    )

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    if selected_tab == "👤 Profile":
        render_profile_tab(user)
    elif selected_tab == "💰 Sales":
        render_sales_tab(user)
    elif selected_tab == "📋 Attendance":
        render_attendance_tab(user)
    elif selected_tab == "☕ Breaks":
        render_breaks_tab(user)
    elif selected_tab == "📞 Callbacks":
        render_callbacks_tab(user)
    elif selected_tab == "🗺️ Maps":
        render_maps_tab(user)
    elif selected_tab == "📊 Reports":              # ✅ جديد
        render_reports_tab(user)
    elif selected_tab == "🛡️ Admin" and is_admin:
        render_admin_tab(user)


def _render_topbar(user):
    role_color = {"admin": "#FF6B6B", "leader": "#FFD166", "employee": "#06D6A0"}
    color = role_color.get(user["role"], "#8B90A8")

    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:0.6rem 0">
            <img src="https://plain-eeur-prod-public.komododecks.com/202608/09/cTbwjWfVAMvKzMZ4n8ET/image.png"
                 style="height:52px;vertical-align:middle;margin-right:10px">
            <span style="font-family:'Space Grotesk',sans-serif;font-size:1.3rem;
                         font-weight:700;background:linear-gradient(135deg,#4F6BFF,#7C3AED);
                         -webkit-background-clip:text;-webkit-text-fill-color:transparent">
                Hunter Portal
            </span>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:center;
                    gap:8px;padding:0.65rem 0">
            <span style="color:#8B90A8;font-size:0.82rem">Logged in as</span>
            <span style="color:#E8EAF0;font-weight:600;font-size:0.9rem">
                {user.get('full_name','User')}
            </span>
            <span style="background:{color}22;color:{color};
                         padding:2px 10px;border-radius:20px;
                         font-size:0.75rem;font-weight:600;text-transform:capitalize;
                         border:1px solid {color}44">
                {user['role']}
            </span>
            <span style="color:#8B90A8;font-size:0.8rem;margin-left:8px">
                {datetime.now().strftime('%A, %d %B %Y  %H:%M')}
            </span>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        if st.button("⏻  Sign Out", key="logout_btn"):
            logout()
    st.markdown('<hr style="border-color:#2E3350;margin:0 0 4px 0">', unsafe_allow_html=True)
