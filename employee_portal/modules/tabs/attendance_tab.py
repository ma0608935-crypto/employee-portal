"""
modules/tabs/attendance_tab.py
Attendance tab — manual check-in with time picker for admin/leader
"""

import streamlit as st
import pandas as pd
import os
from datetime import date, datetime, timedelta
from modules.database import record_attendance, get_attendance, get_all_users

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
ATT_FILE = os.path.join(DATA_DIR, "attendance.xlsx")

# وقت الحضور المتوقع (5:00 PM)
EXPECTED_HOUR = 17
EXPECTED_MINUTE = 0

# المنطقة الزمنية الافتراضية (مصر: UTC+2)
DEFAULT_TZ_HOURS = 2
DEFAULT_TZ_MINUTES = 0


def _sync_excel(records):
    os.makedirs(DATA_DIR, exist_ok=True)
    pd.DataFrame(records).to_excel(ATT_FILE, index=False)


def _is_late(check_hour, check_minute):
    """Check if the check-in time is late (after 5:00 PM)."""
    if check_hour > EXPECTED_HOUR:
        return True
    elif check_hour == EXPECTED_HOUR and check_minute > EXPECTED_MINUTE:
        return True
    return False


def _get_local_time():
    """
    Get local time based on system timezone setting (hours + minutes).
    """
    # Check if timezone is set in session
    if "system_tz_hours" in st.session_state and "system_tz_minutes" in st.session_state:
        offset_hours = st.session_state.system_tz_hours
        offset_minutes = st.session_state.system_tz_minutes
        total_minutes = offset_hours * 60 + offset_minutes
        utc_now = datetime.utcnow()
        local_now = utc_now + timedelta(minutes=total_minutes)
        return local_now
    
    # Fallback to default
    utc_now = datetime.utcnow()
    local_now = utc_now + timedelta(hours=DEFAULT_TZ_HOURS, minutes=DEFAULT_TZ_MINUTES)
    return local_now


def render_attendance_tab(user: dict):
    is_admin = user["role"] in ("admin", "leader")
    today_str = date.today().isoformat()
    
    # ── Initialize timezone in session if not exists ────────────────────────
    if "system_tz_hours" not in st.session_state:
        st.session_state.system_tz_hours = DEFAULT_TZ_HOURS
    if "system_tz_minutes" not in st.session_state:
        st.session_state.system_tz_minutes = DEFAULT_TZ_MINUTES
    
    # ── Timezone Settings (Admin/Leader Only) ───────────────────────────────
    if is_admin:
        with st.expander("🌍 System Timezone Settings (Admin Only)", expanded=True):
            st.markdown("""
            <div style="background:#1A1D27;border:1px solid #2E3350;border-radius:8px;padding:0.75rem;margin-bottom:0.75rem;">
                <p style="color:#8B90A8;font-size:0.85rem;">
                    <strong>⚠️ Admin Only:</strong> Set the system timezone for all users.
                    <br>Examples: Egypt = +2:00, India = +5:30, Nepal = +5:45
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Get current values from session
            current_hours = st.session_state.system_tz_hours
            current_minutes = st.session_state.system_tz_minutes
            
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                new_tz_hours = st.number_input(
                    "UTC Offset (Hours)",
                    min_value=-12,
                    max_value=14,
                    value=current_hours,
                    step=1,
                    key="tz_hours_input"
                )
            with col2:
                new_tz_minutes = st.selectbox(
                    "Minutes",
                    [0, 15, 30, 45],
                    index=[0, 15, 30, 45].index(current_minutes) if current_minutes in [0, 15, 30, 45] else 0,
                    key="tz_minutes_input"
                )
            with col3:
                if st.button("✅ Apply to All Users", key="apply_tz_btn"):
                    # Save to session state
                    st.session_state.system_tz_hours = new_tz_hours
                    st.session_state.system_tz_minutes = new_tz_minutes
                    
                    total_minutes = new_tz_hours * 60 + new_tz_minutes
                    hours_display = total_minutes // 60
                    mins_display = abs(total_minutes % 60)
                    sign = "+" if total_minutes >= 0 else ""
                    
                    st.success(f"✅ System timezone set to UTC{sign}{hours_display}:{mins_display:02d} for all users!")
                    st.rerun()
            
            # Show current system time
            local_now = _get_local_time()
            server_now = datetime.utcnow()
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("🕐 System Local Time", local_now.strftime("%I:%M:%S %p"))
            with col_b:
                st.metric("🖥️ Server Time (UTC)", server_now.strftime("%I:%M:%S %p"))
            
            total_minutes = current_hours * 60 + current_minutes
            hours_display = total_minutes // 60
            mins_display = abs(total_minutes % 60)
            sign = "+" if total_minutes >= 0 else ""
            st.info(f"✅ Current system timezone: UTC{sign}{hours_display}:{mins_display:02d}")

    # ── Show current time for all users ──────────────────────────────────────
    else:
        # Regular employees see a small indicator
        local_now = _get_local_time()
        tz_hours = st.session_state.system_tz_hours
        tz_minutes = st.session_state.system_tz_minutes
        total_minutes = tz_hours * 60 + tz_minutes
        hours_display = total_minutes // 60
        mins_display = abs(total_minutes % 60)
        sign = "+" if total_minutes >= 0 else ""
        st.caption(f"🕐 System time: {local_now.strftime('%I:%M:%S %p')} (UTC{sign}{hours_display}:{mins_display:02d})")

    st.markdown("---")
    
    local_now = _get_local_time()

    # ── Admin/Leader: Can set check-in time for any employee ────────────────
    if is_admin:
        st.markdown("### 🛡️ Admin — Manage Attendance")
        
        tab1, tab2 = st.tabs(["📋 Record Check-in", "✅ My Check-in"])
        
        with tab1:
            employees = [e for e in get_all_users() if e["role"] == "employee"]
            if not employees:
                st.info("No employees found.")
            else:
                emp_options = {
                    f"{e.get('full_name','')} ({e.get('employee_id','')})": e
                    for e in employees
                }
                
                col1, col2 = st.columns(2)
                with col1:
                    selected_label = st.selectbox("Select Employee", list(emp_options.keys()), key="att_admin_emp")
                with col2:
                    check_date = st.date_input("Date", value=date.today(), key="att_admin_date")
                
                # Time picker in 12-hour format
                col3, col4 = st.columns(2)
                with col3:
                    check_hour = st.number_input("Hour", min_value=1, max_value=12, value=5, key="att_admin_hour")
                with col4:
                    check_minute = st.selectbox("Minute", [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55], index=0, key="att_admin_min")
                
                am_pm = st.selectbox("AM/PM", ["AM", "PM"], index=1, key="att_admin_ampm")
                
                # Status selection
                status_opt = st.selectbox("Status", ["Present", "Late", "Absent"], key="att_admin_status")
                
                if st.button("📍 Record Check-in", key="admin_checkin_btn", use_container_width=True):
                    emp = emp_options[selected_label]
                    
                    # Convert to 24-hour format
                    hour_24 = check_hour
                    if am_pm == "PM" and check_hour != 12:
                        hour_24 = check_hour + 12
                    elif am_pm == "AM" and check_hour == 12:
                        hour_24 = 0
                    
                    time_str = f"{hour_24:02d}:{check_minute:02d}:00"
                    date_str = check_date.isoformat()
                    
                    ok, msg = record_attendance(
                        emp.get("employee_id"),
                        emp.get("full_name"),
                        date_str,
                        time_str,
                        status_opt
                    )
                    if ok:
                        _sync_excel(get_attendance())
                        st.success(f"✅ Check-in recorded for {emp.get('full_name')} at {check_hour}:{check_minute:02d} {am_pm}")
                        st.rerun()
                    else:
                        st.warning(msg)
        
        with tab2:
            _employee_checkin_block(user, today_str, is_admin=True)
    
    # ── Employee View ────────────────────────────────────────────────────────
    else:
        st.markdown("### 📋 Check-in")
        _employee_checkin_block(user, today_str, is_admin=False)

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    # ── Metrics ───────────────────────────────────────────────────────────────
    records = get_attendance(None if is_admin else user.get("employee_id"))
    today_obj = date.today()
    week_start = today_obj - timedelta(days=today_obj.weekday())
    month_start = today_obj.replace(day=1)

    today_cnt = sum(1 for r in records if r["date"] == today_str)
    week_cnt = sum(1 for r in records if r["date"] >= week_start.isoformat())
    month_cnt = sum(1 for r in records if r["date"] >= month_start.isoformat())
    total = len(records)
    present = sum(1 for r in records if r["status"] == "Present")
    late = sum(1 for r in records if r["status"] == "Late")
    att_rate = round(present / total * 100) if total else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("✅ Today", today_cnt)
    with c2:
        st.metric("📅 This Week", week_cnt)
    with c3:
        st.metric("📆 This Month", month_cnt)
    with c4:
        st.metric("📊 Rate", f"{att_rate}%")
    with c5:
        st.metric("⏰ Late", late)
    with c6:
        st.metric("❌ Absent", total - present - late)

    # ── Charts ────────────────────────────────────────────────────────────────
    try:
        import plotly.express as px
        df = pd.DataFrame(records)
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            col_l, col_r = st.columns(2)
            with col_l:
                daily = df.groupby("date").size().reset_index(name="count")
                fig = px.bar(daily, x="date", y="count", title="Daily Attendance",
                             template="plotly_dark", color_discrete_sequence=["#4F6BFF"])
                fig.update_layout(paper_bgcolor="#1A1D27", plot_bgcolor="#1A1D27",
                                  font_color="#C8CADE", margin=dict(l=10, r=10, t=40, b=10),
                                  title_font_size=13)
                st.plotly_chart(fig, use_container_width=True)
            with col_r:
                sc = df["status"].value_counts().reset_index()
                sc.columns = ["Status", "Count"]
                fig2 = px.pie(sc, values="Count", names="Status",
                              title="Status Distribution", template="plotly_dark",
                              color_discrete_sequence=["#06D6A0", "#FFD166", "#FF6B6B"])
                fig2.update_layout(paper_bgcolor="#1A1D27", font_color="#C8CADE",
                                   margin=dict(l=10, r=10, t=40, b=10), title_font_size=13)
                st.plotly_chart(fig2, use_container_width=True)
    except ImportError:
        pass

    # ── Table ─────────────────────────────────────────────────────────────────
    st.markdown("#### 📋 Attendance Records")
    df_show = pd.DataFrame(records)
    if not df_show.empty:
        show_cols = [c for c in ["employee_id", "full_name", "date", "check_in", "status"]
                     if c in df_show.columns]
        st.dataframe(df_show[show_cols], use_container_width=True, height=300)
        if is_admin:
            st.download_button("⬇️ Export CSV",
                               df_show.to_csv(index=False).encode(),
                               "attendance.csv", "text/csv")


def _employee_checkin_block(user, today_str, is_admin=False):
    """Check-in block for employees (auto time) and admin/leader (manual time)."""
    
    today_records = [a for a in get_attendance(user.get("employee_id"))
                     if a["date"] == today_str]
    
    if today_records:
        r = today_records[0]
        check_in_time = r.get('check_in', '')
        status = r["status"]
        
        # Convert 24h to 12h format for display
        try:
            time_obj = datetime.strptime(check_in_time, "%H:%M:%S")
            display_time = time_obj.strftime("%I:%M %p").lstrip("0")
        except:
            display_time = check_in_time
        
        badge_class = "badge-present" if status == "Present" else "badge-late"
        status_text = "✅ Present" if status == "Present" else "⏰ Late"
        
        st.markdown(f"""
        <div class="checkin-status checked">
            <div style="font-size:1.2rem;font-weight:600;color:#E8EAF0;">
                ✅ Checked in
            </div>
            <div style="color:#C8CADE;font-size:1rem;margin-top:4px;">
                🕐 {display_time}
            </div>
            <div style="margin-top:6px;">
                <span class="status-badge {badge_class}">{status_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.button(
            "✅ Already checked in",
            disabled=True,
            use_container_width=True,
            key=f"checkin_disabled_{user['id']}"
        )
    else:
        local_now = _get_local_time()
        
        if is_admin:
            # Admin/Leader: can pick time
            st.info("You are an admin. You can set a custom check-in time.")
            
            col1, col2 = st.columns(2)
            with col1:
                check_hour = st.number_input("Hour", min_value=1, max_value=12, value=5, key=f"emp_hour_{user['id']}")
            with col2:
                check_minute = st.selectbox("Minute", [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55], index=0, key=f"emp_min_{user['id']}")
            
            am_pm = st.selectbox("AM/PM", ["AM", "PM"], index=1, key=f"emp_ampm_{user['id']}")
            status_opt = st.selectbox("Status", ["Present", "Late"], key=f"emp_status_{user['id']}")
            
            if st.button("📍 Check In", key=f"checkin_admin_{user['id']}", use_container_width=True):
                # Convert to 24-hour format
                hour_24 = check_hour
                if am_pm == "PM" and check_hour != 12:
                    hour_24 = check_hour + 12
                elif am_pm == "AM" and check_hour == 12:
                    hour_24 = 0
                
                time_str = f"{hour_24:02d}:{check_minute:02d}:00"
                
                # Auto-detect if late
                is_late = _is_late(hour_24, check_minute)
                final_status = "Late" if is_late else status_opt
                
                ok, msg = record_attendance(
                    user.get("employee_id"),
                    user.get("full_name"),
                    today_str,
                    time_str,
                    final_status
                )
                if ok:
                    st.success(f"✅ Checked in at {check_hour}:{check_minute:02d} {am_pm}")
                    _sync_excel(get_attendance())
                    st.rerun()
                else:
                    st.warning(msg)
        else:
            # Employee: auto check-in using local time
            is_late = _is_late(local_now.hour, local_now.minute)
            
            if is_late:
                st.warning(f"⏰ Late! Current time: {local_now.strftime('%I:%M %p')} (Expected before 5:00 PM)")
            else:
                st.success(f"✅ On time! Current time: {local_now.strftime('%I:%M %p')}")
            
            if st.button("📍 Check In Now", key=f"checkin_{user['id']}", use_container_width=True):
                local_now = _get_local_time()
                time_str = local_now.strftime("%H:%M:%S")
                status = "Late" if _is_late(local_now.hour, local_now.minute) else "Present"
                
                ok, msg = record_attendance(
                    user.get("employee_id"),
                    user.get("full_name"),
                    today_str,
                    time_str,
                    status
                )
                if ok:
                    st.success(f"✅ Checked in at {local_now.strftime('%I:%M %p')}")
                    _sync_excel(get_attendance())
                    st.rerun()
                else:
                    st.warning(msg)
