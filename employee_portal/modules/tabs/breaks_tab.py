"""
modules/tabs/breaks_tab.py
Break management — only for current user (admin/leader see only their own)
"""

import streamlit as st
import pandas as pd
import os
import json
from datetime import date, datetime, timedelta
from modules.database import start_break, end_break, get_open_break, get_breaks, get_break_schedule, save_break_schedule, get_timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
BREAK_FILE = os.path.join(DATA_DIR, "breaks.xlsx")


def _get_local_time():
    """Get local time based on system timezone setting."""
    hours, minutes = get_timezone()
    total_minutes = hours * 60 + minutes
    utc_now = datetime.utcnow()
    local_now = utc_now + timedelta(minutes=total_minutes)
    return local_now


def _sync_excel():
    os.makedirs(DATA_DIR, exist_ok=True)
    records = get_breaks()
    pd.DataFrame(records).to_excel(BREAK_FILE, index=False)


def _convert_to_12h(time_str):
    """Convert 24-hour format to 12-hour format for display."""
    try:
        time_obj = datetime.strptime(time_str, "%H:%M")
        return time_obj.strftime("%I:%M %p").lstrip("0")
    except:
        return time_str


def render_breaks_tab(user: dict):
    is_admin = user["role"] in ("admin", "leader")
    today_str = date.today().isoformat()
    
    # ── Load break schedule from database ───────────────────────────────────
    BREAKS = get_break_schedule()

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

    # ── Admin: Edit break schedule (saves to database) ──────────────────────
    if is_admin:
        with st.expander("⚙️ Edit Break Schedule (Applies to All Users)", expanded=False):
            st.markdown("""
            <div style="background:rgba(79,107,255,0.08);border:1px solid rgba(79,107,255,0.2);
                        border-radius:8px;padding:0.75rem;margin-bottom:0.75rem;">
                <p style="color:#8B90A8;font-size:0.85rem;">
                    ⚠️ <strong>Admin Only:</strong> Changes to the break schedule will apply to <strong>ALL</strong> users immediately.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            new_schedule = []
            cols = st.columns(3)
            for i, brk in enumerate(BREAKS):
                with cols[i]:
                    st.markdown(f"**{brk['emoji']} {brk['name']}**")
                    
                    # Start time (12-hour format)
                    col_h, col_m, col_ampm = st.columns(3)
                    start_h = int(brk["start"].split(":")[0])
                    start_h_12 = start_h if start_h <= 12 else start_h - 12
                    start_ampm_default = "PM" if start_h >= 12 else "AM"
                    if start_h == 0:
                        start_h_12 = 12
                        start_ampm_default = "AM"
                    if start_h == 12:
                        start_ampm_default = "PM"
                    
                    with col_h:
                        new_start_h = st.number_input("H", min_value=1, max_value=12, value=start_h_12, key=f"brk_start_h_{i}")
                    with col_m:
                        new_start_m = st.selectbox("M", [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55], 
                                                   index=[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].index(int(brk["start"].split(":")[1])), 
                                                   key=f"brk_start_m_{i}")
                    with col_ampm:
                        new_start_ampm = st.selectbox("AM/PM", ["AM", "PM"], 
                                                      index=0 if start_ampm_default == "AM" else 1, 
                                                      key=f"brk_start_ampm_{i}")
                    
                    # Convert to 24-hour
                    start_h_24 = new_start_h
                    if new_start_ampm == "PM" and new_start_h != 12:
                        start_h_24 = new_start_h + 12
                    elif new_start_ampm == "AM" and new_start_h == 12:
                        start_h_24 = 0
                    start_24 = f"{start_h_24:02d}:{new_start_m:02d}"
                    
                    # End time (12-hour format)
                    col_h2, col_m2, col_ampm2 = st.columns(3)
                    end_h = int(brk["end"].split(":")[0])
                    end_h_12 = end_h if end_h <= 12 else end_h - 12
                    end_ampm_default = "PM" if end_h >= 12 else "AM"
                    if end_h == 0:
                        end_h_12 = 12
                        end_ampm_default = "AM"
                    if end_h == 12:
                        end_ampm_default = "PM"
                    
                    with col_h2:
                        new_end_h = st.number_input("H", min_value=1, max_value=12, value=end_h_12, key=f"brk_end_h_{i}")
                    with col_m2:
                        new_end_m = st.selectbox("M", [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55],
                                                 index=[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].index(int(brk["end"].split(":")[1])),
                                                 key=f"brk_end_m_{i}")
                    with col_ampm2:
                        new_end_ampm = st.selectbox("AM/PM", ["AM", "PM"],
                                                    index=0 if end_ampm_default == "AM" else 1,
                                                    key=f"brk_end_ampm_{i}")
                    
                    # Convert to 24-hour
                    end_h_24 = new_end_h
                    if new_end_ampm == "PM" and new_end_h != 12:
                        end_h_24 = new_end_h + 12
                    elif new_end_ampm == "AM" and new_end_h == 12:
                        end_h_24 = 0
                    end_24 = f"{end_h_24:02d}:{new_end_m:02d}"
                    
                    new_schedule.append({
                        "name": brk["name"],
                        "emoji": brk["emoji"],
                        "start": start_24,
                        "end": end_24,
                    })
            
            if st.button("💾 Save Break Schedule (Apply to All)", key="save_brk_schedule"):
                save_break_schedule(new_schedule)
                st.success("✅ Break schedule updated for ALL users!")
                st.rerun()

    # ── Break cards (using schedule from database) ──────────────────────────
    st.markdown("### ☕ Break Schedule")
    cols = st.columns(3)
    for i, brk in enumerate(BREAKS):
        with cols[i]:
            open_rec = get_open_break(user.get("employee_id"), brk["name"], today_str)
            today_breaks = [b for b in get_breaks(user.get("employee_id"))
                            if b["date"] == today_str
                            and b["break_name"] == brk["name"]
                            and b.get("end_time")]
            is_done = bool(today_breaks)

            card_class = "break-done" if is_done else ("break-active" if open_rec else "")
            st.markdown(f'<div class="break-card {card_class}">', unsafe_allow_html=True)
            st.markdown(f'<div class="break-name">{brk["emoji"]} {brk["name"]}</div>',
                        unsafe_allow_html=True)
            
            # Display in 12-hour format
            start_display = _convert_to_12h(brk["start"])
            end_display = _convert_to_12h(brk["end"])
            st.markdown(f'<div class="break-time">🕐 {start_display} – {end_display}</div>',
                        unsafe_allow_html=True)

            if is_done:
                dur = today_breaks[0].get("duration", 0)
                st.markdown(f'<div style="color:#06D6A0;font-size:0.85rem">✅ Done ({dur:.0f} min)</div>',
                            unsafe_allow_html=True)
            elif open_rec:
                start_display = _convert_to_12h(open_rec["start_time"][:5])
                st.markdown(f'<div style="color:#4F6BFF;font-size:0.82rem">🔴 In progress since {start_display}</div>',
                            unsafe_allow_html=True)
                if st.button("⏹️ End Break", key=f"end_{i}"):
                    local_now = _get_local_time()
                    start_dt = datetime.strptime(
                        f"{today_str} {open_rec['start_time']}", "%Y-%m-%d %H:%M:%S")
                    duration = (local_now - start_dt).seconds / 60
                    end_break(open_rec["id"], local_now.strftime("%H:%M:%S"), round(duration, 2))
                    _sync_excel()
                    st.rerun()
            else:
                if st.button("▶️ Start Break", key=f"start_{i}"):
                    local_now = _get_local_time()
                    start_break(
                        user.get("employee_id"), user.get("full_name"),
                        brk["name"], local_now.strftime("%H:%M:%S"), today_str)
                    _sync_excel()
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    # ── Filters ──────────────────────────────────────────────────────────────
    all_breaks = get_breaks(user.get("employee_id"))
    
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        date_filter = st.date_input("Filter by Date", value=None, key="brk_date")
    with c2:
        brk_names = ["All"] + [b["name"] for b in BREAKS]
        brk_type_filter = st.selectbox("Break Type", brk_names, key="brk_type")
    with c3:
        search = st.text_input("🔍 Search", key="brk_search")

    filtered = all_breaks[:]
    if date_filter:
        filtered = [b for b in filtered if b.get("date") == str(date_filter)]
    if brk_type_filter != "All":
        filtered = [b for b in filtered if b.get("break_name") == brk_type_filter]
    if search:
        filtered = [b for b in filtered
                    if search.lower() in (b.get("full_name", "") or "").lower()
                    or search.lower() in (b.get("employee_id", "") or "").lower()]

    # ── Metrics ──────────────────────────────────────────────────────────────
    completed_brks = [b for b in all_breaks if b.get("duration")]
    total_min = sum(b["duration"] for b in completed_brks)
    avg_min = total_min / len(completed_brks) if completed_brks else 0
    in_prog = sum(1 for b in all_breaks if not b.get("end_time"))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Breaks", len(completed_brks))
    with c2:
        st.metric("Total Time", f"{int(total_min)} min")
    with c3:
        st.metric("Avg Duration", f"{avg_min:.1f} min")
    with c4:
        st.metric("In Progress", in_prog)

    # ── Table ────────────────────────────────────────────────────────────────
    if filtered:
        df = pd.DataFrame(filtered)
        cols_show = [c for c in ["employee_id", "full_name", "break_name",
                                  "date", "start_time", "end_time", "duration"]
                     if c in df.columns]
        df_show = df[cols_show]
        
        # Convert times to 12-hour format for display
        if "start_time" in df_show.columns:
            df_show["start_time"] = df_show["start_time"].apply(lambda x: _convert_to_12h(x[:5]) if x else x)
        if "end_time" in df_show.columns:
            df_show["end_time"] = df_show["end_time"].apply(lambda x: _convert_to_12h(x[:5]) if x else x)
        
        st.markdown("#### Your Break History")
        st.dataframe(df_show.reset_index(drop=True), use_container_width=True, height=320)
    else:
        st.info("No break records found for the selected filters.")
