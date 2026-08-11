"""
modules/tabs/callbacks_tab.py
Callback management — CRUD, Google Sheets sync, dashboard, filters.
"""

import streamlit as st
import pandas as pd
import os
from datetime import date
from modules.database import add_callback, update_callback, delete_callback, get_callbacks

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
CB_FILE  = os.path.join(DATA_DIR, "callbacks.xlsx")

STATUS_OPTS = ["Pending","Completed","Cancelled"]
STATUS_COLORS = {
    "Pending":   ("#FFD166","#FFD16622"),
    "Completed": ("#06D6A0","#06D6A022"),
    "Cancelled": ("#FF6B6B","#FF6B6B22"),
}


def _sync_excel():
    os.makedirs(DATA_DIR, exist_ok=True)
    pd.DataFrame(get_callbacks()).to_excel(CB_FILE, index=False)


def _push_to_sheets(df: pd.DataFrame, url: str):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_dict = st.secrets.get("gcp_service_account", {})
        if not creds_dict:
            return False, "No GCP service account in secrets.toml"
        creds = Credentials.from_service_account_info(
            dict(creds_dict),
            scopes=["https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive"])
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(url)
        ws = sh.sheet1
        ws.clear()
        ws.update([df.columns.tolist()] + df.fillna("").values.tolist())
        return True, "Synced to Google Sheets!"
    except Exception as e:
        return False, str(e)


def render_callbacks_tab(user: dict):
    is_admin = user["role"] in ("admin","leader")
    is_employee = user["role"] == "employee"

    st.markdown("""
    <style>
    .cb-card { background:#1A1D27;border:1px solid #2E3350;border-radius:14px;
               padding:1rem;margin-bottom:0.6rem; }
    .cb-name  { font-weight:600;color:#E8EAF0;font-size:0.95rem; }
    .cb-phone { color:#8B90A8;font-size:0.82rem; }
    .cb-dt    { color:#C8CADE;font-size:0.82rem; }
    .status-pill { display:inline-block;padding:3px 12px;border-radius:20px;
                   font-size:0.75rem;font-weight:600; }
    </style>
    """, unsafe_allow_html=True)

    # ── Google Sheets config (admin only) ─────────────────────────────────────
    if is_admin:
        with st.expander("🔗 Google Sheets Integration", expanded=False):
            col1, col2 = st.columns([4,1])
            with col1:
                sheet_url = st.text_input(
                    "Callbacks Google Sheets URL",
                    value=st.session_state.get("callbacks_sheet_url",""),
                    placeholder="https://docs.google.com/spreadsheets/d/...",
                    key="callbacks_sheet_input",
                    label_visibility="collapsed"
                )
            with col2:
                if st.button("💾 Save", key="save_cb_url"):
                    st.session_state.callbacks_sheet_url = sheet_url
                    st.success("Saved!")
            st.caption("Share the sheet with your service account email as Editor.")
            if st.button("🔄 Sync All Callbacks Now", key="sync_cb_now"):
                df = pd.DataFrame(get_callbacks())
                ok, msg = _push_to_sheets(df, st.session_state.get("callbacks_sheet_url",""))
                st.success(msg) if ok else st.error(msg)

    callbacks = get_callbacks(None if is_admin else user.get("employee_id"))

    # ── Dashboard ─────────────────────────────────────────────────────────────
    total     = len(callbacks)
    pending   = sum(1 for c in callbacks if c["status"]=="Pending")
    completed = sum(1 for c in callbacks if c["status"]=="Completed")
    cancelled = sum(1 for c in callbacks if c["status"]=="Cancelled")
    rate      = round(completed/total*100) if total else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("Total",           total)
    with c2: st.metric("Pending",         pending)
    with c3: st.metric("Completed",       completed)
    with c4: st.metric("Cancelled",       cancelled)
    with c5: st.metric("Completion Rate", f"{rate}%")

    try:
        import plotly.express as px
        if callbacks:
            sc = pd.DataFrame({"Status":["Pending","Completed","Cancelled"],
                               "Count":[pending,completed,cancelled]})
            fig = px.bar(sc, x="Status", y="Count", color="Status",
                         template="plotly_dark",
                         color_discrete_map={"Pending":"#FFD166","Completed":"#06D6A0","Cancelled":"#FF6B6B"},
                         title="Callback Status Overview")
            fig.update_layout(paper_bgcolor="#1A1D27",plot_bgcolor="#1A1D27",
                               font_color="#C8CADE",showlegend=False,
                               margin=dict(l=10,r=10,t=40,b=10),title_font_size=13)
            st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        pass

    st.markdown("---")

    # ── Add callback ── ONLY FOR EMPLOYEES ──────────────────────────────────
    if is_employee:
        with st.expander("➕ Add New Callback", expanded=False):
            with st.form("add_cb_form"):
                c1,c2 = st.columns(2)
                with c1:
                    cust    = st.text_input("Customer Name *")
                    phone   = st.text_input("Phone Number *")
                    cb_date = st.date_input("Callback Date", value=date.today())
                with c2:
                    cb_time = st.time_input("Callback Time")
                    status  = st.selectbox("Status", STATUS_OPTS)
                    notes   = st.text_area("Notes", height=80)
                if st.form_submit_button("💾 Save Callback"):
                    if not cust or not phone:
                        st.error("Customer Name and Phone are required.")
                    else:
                        add_callback(user.get("employee_id"), cust, phone,
                                     cb_date.isoformat(), str(cb_time), status, notes)
                        _sync_excel()
                        # Auto-push to sheets if configured
                        sheet_url = st.session_state.get("callbacks_sheet_url","")
                        if sheet_url and is_admin:
                            _push_to_sheets(pd.DataFrame(get_callbacks()), sheet_url)
                        st.success("Callback added!")
                        st.rerun()
    else:
        # Admin/Leader sees a message instead of the add form
        st.info("👀 You are viewing all employee callbacks. Only employees can add new callbacks.")

    # ── Filters ───────────────────────────────────────────────────────────────
    c1,c2,c3 = st.columns([2,2,2])
    with c1: stat_f = st.selectbox("Filter Status",["All"]+STATUS_OPTS, key="cb_stat")
    with c2: date_f = st.date_input("Filter Date", value=None, key="cb_date")
    with c3: search = st.text_input("🔍 Search Customer", key="cb_search")

    filtered = callbacks[:]
    if stat_f  != "All":     filtered = [c for c in filtered if c["status"] == stat_f]
    if date_f:               filtered = [c for c in filtered if c.get("callback_date") == str(date_f)]
    if search:               filtered = [c for c in filtered
                                         if search.lower() in (c.get("customer_name","") or "").lower()
                                         or search.lower() in (c.get("phone","") or "").lower()]

    # ── Cards ─────────────────────────────────────────────────────────────────
    st.markdown(f"#### Callbacks ({len(filtered)} records)")
    for cb in filtered:
        col_text, col_stat, col_actions = st.columns([4,1,2])
        txt_color, bg_color = STATUS_COLORS.get(cb["status"], ("#8B90A8","#1A1D27"))
        with col_text:
            st.markdown(f"""
            <div class="cb-card">
                <div class="cb-name">👤 {cb.get('customer_name','—')}</div>
                <div class="cb-phone">📱 {cb.get('phone','—')}</div>
                <div class="cb-dt">📅 {cb.get('callback_date','—')} &nbsp; 🕐 {cb.get('callback_time','—')}</div>
                {f'<div style="color:#8B90A8;font-size:0.78rem;margin-top:3px">📝 {cb.get("notes","")}</div>' if cb.get("notes") else ""}
            </div>""", unsafe_allow_html=True)
        with col_stat:
            st.markdown(f"""
            <div style="padding-top:1rem">
                <span class="status-pill"
                      style="color:{txt_color};background:{bg_color};border:1px solid {txt_color}55">
                    {cb['status']}
                </span>
            </div>""", unsafe_allow_html=True)
        with col_actions:
            st.markdown('<div style="padding-top:0.5rem">', unsafe_allow_html=True)
            new_stat = st.selectbox("", STATUS_OPTS,
                                    index=STATUS_OPTS.index(cb["status"]),
                                    key=f"stat_sel_{cb['id']}",
                                    label_visibility="collapsed")
            col_u, col_d = st.columns(2)
            with col_u:
                if st.button("💾", key=f"upd_{cb['id']}", help="Update status"):
                    update_callback(cb["id"], status=new_stat)
                    _sync_excel()
                    st.rerun()
            with col_d:
                if st.button("🗑️", key=f"del_{cb['id']}", help="Delete"):
                    delete_callback(cb["id"])
                    _sync_excel()
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    if not filtered:
        st.info("No callbacks match the current filters.")

    # ── Export (admin only) ───────────────────────────────────────────────────
    if filtered and is_admin:
        df = pd.DataFrame(filtered)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Export CSV", df.to_csv(index=False).encode(),
                               "callbacks.csv","text/csv")
        with c2:
            sheet_url = st.session_state.get("callbacks_sheet_url","")
            if sheet_url and st.button("📤 Push to Google Sheets", key="push_cb_btn"):
                ok, msg = _push_to_sheets(df, sheet_url)
                st.success(msg) if ok else st.error(msg)