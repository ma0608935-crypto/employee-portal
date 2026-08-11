"""
modules/tabs/callbacks_tab.py
Callback management — CRUD, Google Sheets sync, dashboard, filters.
"""

import streamlit as st
import pandas as pd
import os
from datetime import date, datetime
from modules.database import add_callback, update_callback, delete_callback, get_callbacks

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
CB_FILE = os.path.join(DATA_DIR, "callbacks.xlsx")

STATUS_OPTS = ["Cold", "Warm", "Hot"]
STATUS_COLORS = {
    "Cold": ("#4F6BFF", "#4F6BFF22"),      # أزرق
    "Warm": ("#FF9F43", "#FF9F4322"),      # برتقالي
    "Hot": ("#FF6B6B", "#FF6B6B22"),       # أحمر
}

# للتوافق مع البيانات القديمة
LEGACY_STATUS_OPTS = ["Pending", "Completed", "Cancelled"]
LEGACY_STATUS_COLORS = {
    "Pending": ("#FFD166", "#FFD16622"),
    "Completed": ("#06D6A0", "#06D6A022"),
    "Cancelled": ("#FF6B6B", "#FF6B6B22"),
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
    is_admin = user["role"] in ("admin", "leader")
    is_employee = user["role"] == "employee"

    st.markdown("""
    <style>
    .cb-card { background:#1A1D27;border:1px solid #2E3350;border-radius:14px;
               padding:1rem;margin-bottom:0.6rem; }
    .cb-name  { font-weight:600;color:#E8EAF0;font-size:0.95rem; }
    .cb-phone { color:#8B90A8;font-size:0.82rem; }
    .cb-address { color:#8B90A8;font-size:0.82rem; }
    .cb-dt    { color:#C8CADE;font-size:0.82rem; }
    .cb-notes { color:#8B90A8;font-size:0.78rem;margin-top:3px; }
    .status-pill { display:inline-block;padding:3px 14px;border-radius:20px;
                   font-size:0.75rem;font-weight:600; }
    </style>
    """, unsafe_allow_html=True)

    # ── Google Sheets config (admin only) ─────────────────────────────────────
    if is_admin:
        with st.expander("🔗 Google Sheets Integration", expanded=False):
            col1, col2 = st.columns([4, 1])
            with col1:
                sheet_url = st.text_input(
                    "Callbacks Google Sheets URL",
                    value=st.session_state.get("callbacks_sheet_url", ""),
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
                ok, msg = _push_to_sheets(df, st.session_state.get("callbacks_sheet_url", ""))
                st.success(msg) if ok else st.error(msg)

    callbacks = get_callbacks(None if is_admin else user.get("employee_id"))

    # ── Dashboard ─────────────────────────────────────────────────────────────
    total = len(callbacks)
    cold = sum(1 for c in callbacks if c["status"] == "Cold")
    warm = sum(1 for c in callbacks if c["status"] == "Warm")
    hot = sum(1 for c in callbacks if c["status"] == "Hot")
    
    # للتوافق مع البيانات القديمة
    pending = sum(1 for c in callbacks if c["status"] in ["Pending", "Cold", "Warm"])
    completed = sum(1 for c in callbacks if c["status"] == "Completed")
    cancelled = sum(1 for c in callbacks if c["status"] == "Cancelled")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total", total)
    with c2:
        st.metric("🔵 Cold", cold)
    with c3:
        st.metric("🟠 Warm", warm)
    with c4:
        st.metric("🔴 Hot", hot)
    with c5:
        completed_count = sum(1 for c in callbacks if c["status"] == "Completed")
        rate = round(completed_count / total * 100) if total else 0
        st.metric("Completion Rate", f"{rate}%")

    try:
        import plotly.express as px
        if callbacks:
            # Count statuses
            status_counts = {}
            for s in ["Cold", "Warm", "Hot", "Pending", "Completed", "Cancelled"]:
                count = sum(1 for c in callbacks if c["status"] == s)
                if count > 0:
                    status_counts[s] = count
            
            if status_counts:
                sc = pd.DataFrame({
                    "Status": list(status_counts.keys()),
                    "Count": list(status_counts.values())
                })
                color_map = {
                    "Cold": "#4F6BFF",
                    "Warm": "#FF9F43",
                    "Hot": "#FF6B6B",
                    "Pending": "#FFD166",
                    "Completed": "#06D6A0",
                    "Cancelled": "#FF6B6B"
                }
                fig = px.bar(sc, x="Status", y="Count", color="Status",
                             template="plotly_dark",
                             color_discrete_map=color_map,
                             title="Callback Status Overview")
                fig.update_layout(paper_bgcolor="#1A1D27", plot_bgcolor="#1A1D27",
                                  font_color="#C8CADE", showlegend=False,
                                  margin=dict(l=10, r=10, t=40, b=10), title_font_size=13)
                st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        pass

    st.markdown("---")

    # ── Add callback ── ONLY FOR EMPLOYEES ──────────────────────────────────
    if is_employee:
        with st.expander("➕ Add New Callback", expanded=False):
            with st.form("add_cb_form"):
                c1, c2 = st.columns(2)
                with c1:
                    cust_name = st.text_input("Customer Full Name *")
                    phone = st.text_input("Phone Number *")
                    address = st.text_input("Address")
                with c2:
                    cb_date = st.date_input("Callback Date", value=date.today())
                    cb_time = st.time_input("Callback Time", value=datetime.now().time())
                    status = st.selectbox("Status", STATUS_OPTS)
                
                notes = st.text_area("Notes", height=80, placeholder="Add any additional notes about this callback...")
                
                # Status color indicator
                status_colors = {
                    "Cold": "🔵 Cold - Not urgent, follow up later",
                    "Warm": "🟠 Warm - Interested, follow up soon",
                    "Hot": "🔴 Hot - Very interested, call immediately"
                }
                st.caption(status_colors.get(status, ""))
                
                if st.form_submit_button("💾 Save Callback"):
                    if not cust_name or not phone:
                        st.error("Customer Name and Phone are required.")
                    else:
                        add_callback(
                            user.get("employee_id"),
                            cust_name,
                            phone,
                            cb_date.isoformat(),
                            cb_time.strftime("%H:%M"),
                            status,
                            f"Address: {address}\nNotes: {notes}" if address else notes
                        )
                        _sync_excel()
                        sheet_url = st.session_state.get("callbacks_sheet_url", "")
                        if sheet_url and is_admin:
                            _push_to_sheets(pd.DataFrame(get_callbacks()), sheet_url)
                        st.success("Callback added successfully! ✅")
                        st.rerun()
    else:
        # Admin/Leader sees a message instead of the add form
        st.info("👀 You are viewing all employee callbacks. Only employees can add new callbacks.")

    # ── Filters ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        # Show all statuses including legacy ones
        all_statuses = ["All"] + STATUS_OPTS + LEGACY_STATUS_OPTS
        stat_f = st.selectbox("Filter Status", all_statuses, key="cb_stat")
    with c2:
        date_f = st.date_input("Filter Date", value=None, key="cb_date")
    with c3:
        search = st.text_input("🔍 Search Customer", key="cb_search")

    filtered = callbacks[:]
    if stat_f != "All":
        filtered = [c for c in filtered if c["status"] == stat_f]
    if date_f:
        filtered = [c for c in filtered if c.get("callback_date") == str(date_f)]
    if search:
        filtered = [c for c in filtered
                    if search.lower() in (c.get("customer_name", "") or "").lower()
                    or search.lower() in (c.get("phone", "") or "").lower()
                    or search.lower() in (c.get("notes", "") or "").lower()]

    # ── Cards ─────────────────────────────────────────────────────────────────
    st.markdown(f"#### Callbacks ({len(filtered)} records)")
    for cb in filtered:
        col_text, col_stat, col_actions = st.columns([4, 1, 2])
        
        # Get color based on status
        if cb["status"] in STATUS_COLORS:
            txt_color, bg_color = STATUS_COLORS.get(cb["status"], ("#8B90A8", "#1A1D27"))
        else:
            txt_color, bg_color = LEGACY_STATUS_COLORS.get(cb["status"], ("#8B90A8", "#1A1D27"))
        
        with col_text:
            # Parse notes to extract address if stored in notes
            notes_text = cb.get("notes", "")
            address_text = ""
            if "Address:" in notes_text:
                parts = notes_text.split("Address:")
                if len(parts) > 1:
                    address_part = parts[1].split("Notes:")
                    address_text = address_part[0].strip() if address_part else ""
                    notes_text = address_part[1].strip() if len(address_part) > 1 else ""
            
            st.markdown(f"""
            <div class="cb-card">
                <div class="cb-name">👤 {cb.get('customer_name', '—')}</div>
                <div class="cb-phone">📱 {cb.get('phone', '—')}</div>
                {f'<div class="cb-address">📍 {address_text}</div>' if address_text else ''}
                <div class="cb-dt">📅 {cb.get('callback_date', '—')} &nbsp; 🕐 {cb.get('callback_time', '—')}</div>
                {f'<div class="cb-notes">📝 {notes_text}</div>' if notes_text else ''}
            </div>""", unsafe_allow_html=True)
        
        with col_stat:
            # Status badge with emoji
            emoji = {"Cold": "🔵", "Warm": "🟠", "Hot": "🔴"}.get(cb["status"], "")
            st.markdown(f"""
            <div style="padding-top:1rem">
                <span class="status-pill"
                      style="color:{txt_color};background:{bg_color};border:1px solid {txt_color}55">
                    {emoji} {cb['status']}
                </span>
            </div>""", unsafe_allow_html=True)
        
        with col_actions:
            if is_employee:
                # Employee can update/delete their own callbacks
                st.markdown('<div style="padding-top:0.5rem">', unsafe_allow_html=True)
                # Show status options including legacy ones for compatibility
                all_status_options = STATUS_OPTS + LEGACY_STATUS_OPTS
                current_status = cb["status"]
                if current_status not in all_status_options:
                    all_status_options = [current_status] + all_status_options
                
                new_stat = st.selectbox("", all_status_options,
                                        index=all_status_options.index(current_status) if current_status in all_status_options else 0,
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
            else:
                st.markdown('<div style="padding-top:1rem;color:#8B90A8;font-size:0.8rem">🔒 Read-only</div>', unsafe_allow_html=True)

    if not filtered:
        st.info("No callbacks match the current filters.")

    # ── Export (admin only) ───────────────────────────────────────────────────
    if filtered and is_admin:
        df = pd.DataFrame(filtered)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Export CSV", df.to_csv(index=False).encode(),
                               "callbacks.csv", "text/csv")
        with c2:
            sheet_url = st.session_state.get("callbacks_sheet_url", "")
            if sheet_url and st.button("📤 Push to Google Sheets", key="push_cb_btn"):
                ok, msg = _push_to_sheets(df, sheet_url)
                st.success(msg) if ok else st.error(msg)
