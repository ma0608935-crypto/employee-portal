"""
modules/tabs/breaks_tab.py
Break management — editable break schedule, Google Sheets sync, history.
"""

import streamlit as st
import pandas as pd
import os
from datetime import date, datetime, timedelta
from modules.database import start_break, end_break, get_open_break, get_breaks

DATA_DIR   = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
BREAK_FILE = os.path.join(DATA_DIR, "breaks.xlsx")

# Default break schedule stored in session state
DEFAULT_BREAKS = [
    {"name": "Break 1", "start": "12:00", "end": "12:30", "emoji": "🌞"},
    {"name": "Break 2", "start": "15:00", "end": "15:30", "emoji": "🌆"},
    {"name": "Break 3", "start": "18:00", "end": "18:30", "emoji": "🌙"},
]


def _get_breaks_schedule():
    if "break_schedule" not in st.session_state:
        st.session_state.break_schedule = DEFAULT_BREAKS.copy()
    return st.session_state.break_schedule


def _sync_excel():
    os.makedirs(DATA_DIR, exist_ok=True)
    records = get_breaks()
    pd.DataFrame(records).to_excel(BREAK_FILE, index=False)


def _push_to_sheets(df: pd.DataFrame):
    """Push break records to Google Sheets via URL (append rows)."""
    url = st.session_state.get("breaks_sheet_url", "")
    if not url:
        return False, "No Google Sheets URL configured."
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        import json, streamlit as st2
        creds_dict = st2.secrets.get("gcp_service_account", {})
        if not creds_dict:
            return False, "No GCP service account in secrets."
        creds = Credentials.from_service_account_info(
            dict(creds_dict),
            scopes=["https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive"])
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(url)
        ws = sh.sheet1
        ws.clear()
        ws.update([df.columns.tolist()] + df.values.tolist())
        return True, "Synced to Google Sheets!"
    except Exception as e:
        return False, str(e)


def render_breaks_tab(user: dict):
    is_admin = user["role"] in ("admin", "leader")
    today_str = date.today().isoformat()
    BREAKS = _get_breaks_schedule()

    st.markdown("""
    <style>
    .break-card {
        background:#1A1D27;border:1px solid #2E3350;border-radius:16px;
        padding:1.25rem;text-align:center;
    }
    .break-name { font-family:'Space Grotesk',sans-serif;font-size:1rem;
                  font-weight:700;color:#E8EAF0;margin-bottom:4px; }
    .break-time { color:#8B90A8;font-size:0.82rem;margin-bottom:0.75rem; }
    .break-active { background:rgba(79,107,255,0.12)!important;border-color:#4F6BFF!important; }
    .break-done   { background:rgba(6,214,160,0.08)!important;border-color:#06D6A055!important; }
    </style>
    """, unsafe_allow_html=True)

    # ── Admin: Edit break schedule ────────────────────────────────────────────
    if is_admin:
        with st.expander("⚙️ Edit Break Schedule", expanded=False):
            st.markdown("**Customize break times — changes apply immediately for everyone.**")
            new_schedule = []
            cols = st.columns(3)
            for i, brk in enumerate(BREAKS):
                with cols[i]:
                    st.markdown(f"**{brk['emoji']} {brk['name']}**")
                    new_start = st.text_input("Start (HH:MM)", value=brk["start"],
                                              key=f"brk_start_{i}")
                    new_end   = st.text_input("End   (HH:MM)", value=brk["end"],
                                              key=f"brk_end_{i}")
                    new_schedule.append({
                        "name":  brk["name"],
                        "emoji": brk["emoji"],
                        "start": new_start,
                        "end":   new_end,
                    })
            if st.button("💾 Save Break Schedule", key="save_brk_schedule"):
                st.session_state.break_schedule = new_schedule
                st.success("Break schedule updated!")
                st.rerun()

    # ── Google Sheets config ──────────────────────────────────────────────────
    if is_admin:
        with st.expander("🔗 Google Sheets Integration", expanded=False):
            sheet_url = st.text_input(
                "Google Sheets URL",
                value=st.session_state.get("breaks_sheet_url", ""),
                placeholder="https://docs.google.com/spreadsheets/d/...",
                key="breaks_sheet_input"
            )
            st.caption("Share the sheet with your service account email as Editor first.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Save URL", key="save_brk_url"):
                    st.session_state.breaks_sheet_url = sheet_url
                    st.success("URL saved!")
            with c2:
                if st.button("🔄 Sync Now", key="sync_brk_sheets"):
                    records = get_breaks()
                    df = pd.DataFrame(records)
                    ok, msg = _push_to_sheets(df)
                    st.success(msg) if ok else st.error(msg)

    # ── Break cards ───────────────────────────────────────────────────────────
    st.markdown("### ☕ Break Schedule")
    cols = st.columns(3)
    for i, brk in enumerate(BREAKS):
        with cols[i]:
            open_rec     = get_open_break(user.get("employee_id"), brk["name"], today_str)
            today_breaks = [b for b in get_breaks(user.get("employee_id"))
                            if b["date"] == today_str
                            and b["break_name"] == brk["name"]
                            and b.get("end_time")]
            is_done = bool(today_breaks)

            card_class = "break-done" if is_done else ("break-active" if open_rec else "")
            st.markdown(f'<div class="break-card {card_class}">', unsafe_allow_html=True)
            st.markdown(f'<div class="break-name">{brk["emoji"]} {brk["name"]}</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="break-time">🕐 {brk["start"]} – {brk["end"]}</div>',
                        unsafe_allow_html=True)

            if is_done:
                dur = today_breaks[0].get("duration", 0)
                st.markdown(f'<div style="color:#06D6A0;font-size:0.85rem">✅ Done ({dur:.0f} min)</div>',
                            unsafe_allow_html=True)
            elif open_rec:
                st.markdown(f'<div style="color:#4F6BFF;font-size:0.82rem">🔴 In progress since {open_rec["start_time"]}</div>',
                            unsafe_allow_html=True)
                if st.button("⏹️ End Break", key=f"end_{i}"):
                    end_dt   = datetime.now()
                    start_dt = datetime.strptime(
                        f"{today_str} {open_rec['start_time']}", "%Y-%m-%d %H:%M:%S")
                    duration = (end_dt - start_dt).seconds / 60
                    end_break(open_rec["id"], end_dt.strftime("%H:%M:%S"), round(duration, 2))
                    _sync_excel()
                    st.rerun()
            else:
                if st.button("▶️ Start Break", key=f"start_{i}"):
                    start_break(
                        user.get("employee_id"), user.get("full_name"),
                        brk["name"], datetime.now().strftime("%H:%M:%S"), today_str)
                    _sync_excel()
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────────────────
    all_breaks = get_breaks(None if is_admin else user.get("employee_id"))
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        date_filter = st.date_input("Filter by Date", value=None, key="brk_date")
    with c2:
        brk_names = ["All"] + [b["name"] for b in BREAKS]
        brk_type_filter = st.selectbox("Break Type", brk_names, key="brk_type")
    with c3:
        search = st.text_input("🔍 Search Employee", key="brk_search")

    filtered = all_breaks[:]
    if date_filter:
        filtered = [b for b in filtered if b.get("date") == str(date_filter)]
    if brk_type_filter != "All":
        filtered = [b for b in filtered if b.get("break_name") == brk_type_filter]
    if search:
        filtered = [b for b in filtered
                    if search.lower() in (b.get("full_name","") or "").lower()
                    or search.lower() in (b.get("employee_id","") or "").lower()]

    # ── Metrics ───────────────────────────────────────────────────────────────
    completed_brks = [b for b in all_breaks if b.get("duration")]
    total_min = sum(b["duration"] for b in completed_brks)
    avg_min   = total_min / len(completed_brks) if completed_brks else 0
    in_prog   = sum(1 for b in all_breaks if not b.get("end_time"))

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Breaks",     len(completed_brks))
    with c2: st.metric("Total Break Time", f"{int(total_min)} min")
    with c3: st.metric("Avg Duration",     f"{avg_min:.1f} min")
    with c4: st.metric("In Progress",      in_prog)

    # ── Table + export (admin only) ───────────────────────────────────────────
    if filtered:
        df = pd.DataFrame(filtered)
        cols_show = [c for c in ["employee_id","full_name","break_name",
                                  "date","start_time","end_time","duration"]
                     if c in df.columns]
        df_show = df[cols_show]
        st.markdown("#### Break History")
        st.dataframe(df_show.reset_index(drop=True), use_container_width=True, height=320)

        if is_admin:
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇️ Download CSV",
                                   df_show.to_csv(index=False).encode(),
                                   "breaks.csv", "text/csv")
            with c2:
                if st.button("📤 Push to Google Sheets", key="push_brk"):
                    ok, msg = _push_to_sheets(df_show)
                    st.success(msg) if ok else st.error(msg)
    else:
        st.info("No break records found for the selected filters.")
