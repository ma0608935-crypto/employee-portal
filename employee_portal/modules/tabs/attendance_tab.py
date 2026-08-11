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

# ✅ وقت الحضور المتوقع (5:00 PM)
EXPECTED_HOUR = 17
EXPECTED_MINUTE = 0


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
    Get local time using JavaScript to detect user's timezone.
    Falls back to server time if not available.
    """
    # Check if we have the user's timezone offset from session
    if "user_timezone_offset" in st.session_state:
        offset_minutes = st.session_state.user_timezone_offset
        # Get UTC time and add offset
        utc_now = datetime.utcnow()
        local_now = utc_now + timedelta(minutes=offset_minutes)
        return local_now
    
    # If no timezone set, return server time
    return datetime.now()


def render_attendance_tab(user: dict):
    is_admin = user["role"] in ("admin", "leader")
    today_str = date.today().isoformat()
    local_now = _get_local_time()

    st.markdown("""
    <style>
    .att-card { background:#1A1D27;border:1px solid #2E3350;border-radius:14px;padding:1.25rem; }
    .status-badge { display:inline-block;padding:3px 12px;border-radius:20px;
                    font-size:0.78rem;font-weight:600; }
    .badge-present { background:#06D6A022;color:#06D6A0;border:1px solid #06D6A055; }
    .badge-late    { background:#FFD16622;color:#FFD166;border:1px solid #FFD16655; }
    .badge-absent  { background:#FF6B6B22;color:#FF6B6B;border:1px solid #FF6B6B55; }
    .checkin-btn {
        background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 12px rgba(79,107,255,0.35) !important;
        width: 100% !important;
    }
    .checkin-btn:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 18px rgba(79,107,255,0.5) !important;
    }
    .checkin-btn:disabled {
        opacity: 0.6 !important;
        cursor: not-allowed !important;
        transform: none !important;
    }
    .checkin-status {
        text-align: center;
        padding: 1rem;
        border-radius: 12px;
        margin-top: 0.5rem;
    }
    .checkin-status.checked {
        background: #06D6A022;
        border: 1px solid #06D6A055;
    }
    .checkin-status.late {
        background: #FFD16622;
        border: 1px solid #FFD16655;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Detect Timezone from Browser ────────────────────────────────────────
    # JavaScript to detect browser timezone offset
    detect_tz_js = """
    <script>
        const timezoneOffset = new Date().getTimezoneOffset();
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'timezone_offset';
        input.value = -timezoneOffset;  // Convert to minutes (negative because JS returns opposite)
        input.id = 'tz_offset_input';
        document.body.appendChild(input);
        
        // Send to Streamlit
        const script = document.createElement('script');
        script.innerHTML = `
            const offset = document.getElementById('tz_offset_input').value;
            const parent = window.parent;
            const data = {timezone_offset: offset};
            parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: data
            }, '*');
        `;
        document.body.appendChild(script);
    </script>
    """
    
    # Try to get timezone from browser using a different approach
    if "user_timezone_offset" not in st.session_state:
        # Use a hidden component to detect timezone
        tz_html = f"""
        <div id="tz_detector">
            <p style="color:#8B90A8;font-size:0.8rem;">🕐 Detecting your local time...</p>
            <p style="color:#8B90A8;font-size:0.7rem;" id="tz_display"></p>
        </div>
        <script>
            function detectTimezone() {{
                const offset = -new Date().getTimezoneOffset();
                const now = new Date();
                const hours = String(now.getHours()).padStart(2, '0');
                const minutes = String(now.getMinutes()).padStart(2, '0');
                const seconds = String(now.getSeconds()).padStart(2, '0');
                const ampm = now.getHours() >= 12 ? 'PM' : 'AM';
                const hour12 = now.getHours() % 12 || 12;
                
                document.getElementById('tz_display').innerHTML = 
                    `🕐 Your local time: ${hour12}:${minutes}:${seconds} ${ampm}`;
                
                // Store timezone offset in session via Streamlit
                const data = {{timezone_offset: offset}};
                const event = new CustomEvent('streamlit:setComponentValue', {{
                    detail: {{value: data}}
                }});
                window.dispatchEvent(event);
            }}
            detectTimezone();
        </script>
        """
        
        # Display the timezone detector
        st.markdown(tz_html, unsafe_allow_html=True)
        
        # Add a button to detect timezone
        if st.button("🕐 Detect My Local Time", key="detect_tz"):
            # Get current time from browser using JavaScript
            detect_js = """
            <script>
                const now = new Date();
                const offset = -now.getTimezoneOffset();
                const hours = String(now.getHours()).padStart(2, '0');
                const minutes = String(now.getMinutes()).padStart(2, '0');
                const seconds = String(now.getSeconds()).padStart(2, '0');
                
                const data = {
                    timezone_offset: offset,
                    local_time: `${hours}:${minutes}:${seconds}`
                };
                
                // Send to Streamlit
                const event = new CustomEvent('streamlit:setComponentValue', {
                    detail: {value: data}
                });
                window.dispatchEvent(event);
            </script>
            """
            st.markdown(detect_js, unsafe_allow_html=True)
            st.success("✅ Timezone detected!")
            st.rerun()

    # Show current local time
    col_tz1, col_tz2 = st.columns([3, 1])
    with col_tz1:
        st.caption(f"🕐 Current time: {local_now.strftime('%I:%M:%S %p')}")
    with col_tz2:
        if "user_timezone_offset" in st.session_state:
            st.caption("✅ Timezone: Detected")

    st.markdown("---")

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
