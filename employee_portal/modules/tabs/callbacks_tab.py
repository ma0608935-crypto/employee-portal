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
    "Cold": ("#4F6BFF", "#4F6BFF22"),
    "Warm": ("#FF9F43", "#FF9F4322"),
    "Hot": ("#FF6B6B", "#FF6B6B22"),
}

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

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📊 Total", total)
    with col2:
        st.metric("🔵 Cold", cold)
    with col3:
        st.metric("🟠 Warm", warm)
    with col4:
        st.metric("🔴 Hot", hot)
    with col5:
        completed_count = sum(1 for c in callbacks if c["status"] == "Completed")
        rate = round(completed_count / total * 100) if total else 0
        st.metric("✅ Rate", f"{rate}%")

    # ── Chart ─────────────────────────────────────────────────────────────────
    try:
        import plotly.express as px
        
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
            
            fig = px.bar(
                sc, x="Status", y="Count", color="Status",
                template="plotly_dark",
                color_discrete_map=color_map,
                title="Callback Status Overview"
            )
            
            fig.update_layout(
                paper_bgcolor="#1A1D27",
                plot_bgcolor="#1A1D27",
                font_color="#C8CADE",
                showlegend=False,
                margin=dict(l=10, r=10, t=35, b=10),
                title_font_size=12,
                height=250,
            )
            fig.update_traces(
                texttemplate='%{y}',
                textposition='outside',
                textfont_size=11
            )
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
                        if address and notes:
                            full_notes = f"📍 Address: {address}\n📝 Notes: {notes}"
                        elif address:
                            full_notes = f"📍 Address: {address}"
                        else:
                            full_notes = notes
                            
                        add_callback(
                            user.get("employee_id"),
                            cust_name,
                            phone,
                            cb_date.isoformat(),
                            cb_time.strftime("%H:%M"),
                            status,
                            full_notes
                        )
                        _sync_excel()
                        sheet_url = st.session_state.get("callbacks_sheet_url", "")
                        if sheet_url and is_admin:
                            _push_to_sheets(pd.DataFrame(get_callbacks()), sheet_url)
                        st.success("Callback added successfully! ✅")
                        st.rerun()
    else:
        st.info("👀 You are viewing all employee callbacks. Only employees can add new callbacks.")

    # ── Filters ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        all_statuses = ["All"] + STATUS_OPTS + LEGACY_STATUS_OPTS
        stat_f = st.selectbox("Filter Status", all_statuses, key="cb_stat")
    with c2:
        date_f = st.date_input("Filter Date", value=None, key="cb_date")
    with c3:
        search = st.text_input("🔍 Search", placeholder="Customer, phone, or notes...", key="cb_search")

    filtered = callbacks[:]
    if stat_f != "All":
        filtered = [c for c in filtered if c["status"] == stat_f]
    if date_f:
        filtered = [c for c in filtered if c.get("callback_date") == str(date_f)]
    if search:
        search_lower = search.lower()
        filtered = [c for c in filtered
                    if search_lower in (c.get("customer_name", "") or "").lower()
                    or search_lower in (c.get("phone", "") or "").lower()
                    or search_lower in (c.get("notes", "") or "").lower()]

    # ── Records ──────────────────────────────────────────────────────────────
    st.markdown(f"#### 📋 Callbacks ({len(filtered)} records)")

    for idx, cb in enumerate(filtered):
        # Extract address and notes
        notes_text = cb.get("notes", "")
        address_text = ""
        
        if "📍 Address:" in notes_text:
            parts = notes_text.split("📍 Address:")
            if len(parts) > 1:
                address_parts = parts[1].split("📝 Notes:")
                address_text = address_parts[0].strip() if address_parts else ""
                notes_text = address_parts[1].strip() if len(address_parts) > 1 else ""
        elif "Address:" in notes_text:
            parts = notes_text.split("Address:")
            if len(parts) > 1:
                address_parts = parts[1].split("Notes:")
                address_text = address_parts[0].strip() if address_parts else ""
                notes_text = address_parts[1].strip() if len(address_parts) > 1 else ""
        
        # Get status class
        emoji = {"Cold": "🔵", "Warm": "🟠", "Hot": "🔴"}.get(cb["status"], "")
        
        # All statuses list for dropdown
        all_statuses_list = ["Cold", "Warm", "Hot", "Pending", "Completed", "Cancelled"]
        current_idx = all_statuses_list.index(cb["status"]) if cb["status"] in all_statuses_list else 0
        
        # ── Card باستخدام st.container و HTML ───────────────────────────────
        with st.container():
            # HTML للكارد كامل
            card_html = f'''
            <div style="
                background: #1A1D27;
                border: 2px solid #2E3350;
                border-radius: 10px;
                padding: 12px 14px;
                margin-bottom: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            ">
                <!-- الصف الأول: الاسم + الحالة -->
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 6px;
                ">
                    <span style="
                        font-weight: 600;
                        color: #E8EAF0;
                        font-size: 16px;
                    ">👤 {cb.get('customer_name', '—')}</span>
                    <span style="
                        display: inline-block;
                        padding: 3px 14px;
                        border-radius: 16px;
                        font-size: 13px;
                        font-weight: 600;
                        background: #4F6BFF22;
                        color: #4F6BFF;
                        border: 1px solid #4F6BFF55;
                    ">{emoji} {cb['status']}</span>
                </div>
                
                <!-- التليفون -->
                <div style="
                    color: #C8CADE;
                    font-size: 15px;
                    margin-top: 2px;
                ">
                    <span style="color: #8B90A8;">📱</span> {cb.get('phone', '—')}
                </div>
            '''
            
            # العنوان لو موجود
            if address_text:
                card_html += f'''
                <div style="
                    color: #C8CADE;
                    font-size: 15px;
                    margin-top: 2px;
                ">
                    <span style="color: #8B90A8;">📍</span> {address_text}
                </div>
                '''
            
            # التاريخ والوقت
            card_html += f'''
                <div style="
                    color: #C8CADE;
                    font-size: 15px;
                    margin-top: 2px;
                ">
                    <span style="color: #8B90A8;">📅</span> {cb.get('callback_date', '—')} &nbsp; 
                    <span style="color: #8B90A8;">⏰</span> {cb.get('callback_time', '—')}
                </div>
            '''
            
            # الملاحظات لو موجودة
            if notes_text and notes_text.strip():
                card_html += f'''
                <div style="
                    color: #8B90A8;
                    font-size: 14px;
                    margin-top: 4px;
                    font-style: italic;
                    border-top: 1px solid #2E3350;
                    padding-top: 4px;
                ">
                    📝 {notes_text}
                </div>
                '''
            
            # الأزرار
            if is_employee:
                card_html += '''
                <div style="
                    display: flex;
                    gap: 8px;
                    align-items: center;
                    margin-top: 10px;
                    padding-top: 8px;
                    border-top: 1px solid #2E3350;
                ">
                '''
                
                # استخدم st.selectbox و st.button جوا HTML
                st.markdown(card_html, unsafe_allow_html=True)
                
                # الأزرار باستخدام Streamlit
                col_sel, col_upd, col_del = st.columns([2, 1, 1])
                with col_sel:
                    new_status = st.selectbox(
                        "",
                        all_statuses_list,
                        index=current_idx,
                        key=f"stat_{cb['id']}",
                        label_visibility="collapsed"
                    )
                with col_upd:
                    if st.button("💾", key=f"upd_{cb['id']}", help="Update status"):
                        update_callback(cb["id"], status=new_status)
                        _sync_excel()
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{cb['id']}", help="Delete"):
                        delete_callback(cb["id"])
                        _sync_excel()
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                card_html += '''
                <div style="
                    margin-top: 8px;
                    padding-top: 6px;
                    border-top: 1px solid #2E3350;
                    color: #8B90A8;
                    font-size: 13px;
                ">
                    🔒 Read-only
                </div>
                '''
                st.markdown(card_html, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

    if not filtered:
        st.info("No callbacks match the current filters.")

    # ── Export ────────────────────────────────────────────────────────────────
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
