"""
modules/tabs/attendance_tab.py
Attendance tab — manual check-in only (QR removed)
"""

import streamlit as st
import pandas as pd
import os
from datetime import date, datetime, timedelta
from modules.database import record_attendance, get_attendance, get_all_users

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
ATT_FILE = os.path.join(DATA_DIR, "attendance.xlsx")


def _sync_excel(records):
    os.makedirs(DATA_DIR, exist_ok=True)
    pd.DataFrame(records).to_excel(ATT_FILE, index=False)


def render_attendance_tab(user: dict):
    is_admin = user["role"] in ("admin", "leader")
    today_str = date.today().isoformat()

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

    # ── Admin: يمكنه تسجيل حضور لأي موظف ─────────────────────────────────────
    if is_admin:
        st.markdown("### 🛡️ Admin — Manage Attendance")
        
        tab1, tab2 = st.tabs(["📋 تسجيل حضور لموظف", "✅ تسجيل حضوري"])
        
        with tab1:
            employees = [e for e in get_all_users() if e["role"] == "employee"]
            if not employees:
                st.info("No employees found.")
            else:
                emp_options = {
                    f"{e.get('full_name','')} ({e.get('employee_id','')})": e
                    for e in employees
                }
                selected_label = st.selectbox("اختر الموظف", list(emp_options.keys()), key="att_admin_emp")
                
                if st.button("📍 تسجيل حضور الآن", key="admin_checkin_btn", use_container_width=True):
                    emp = emp_options[selected_label]
                    now = datetime.now()
                    today_str = now.date().isoformat()
                    time_str = now.strftime("%H:%M:%S")
                    
                    # تحديد الحالة (Late لو بعد 9:15)
                    is_late = now.time() > datetime.strptime("09:15", "%H:%M").time()
                    status = "Late" if is_late else "Present"
                    
                    ok, msg = record_attendance(
                        emp.get("employee_id"),
                        emp.get("full_name"),
                        today_str,
                        time_str,
                        status
                    )
                    if ok:
                        _sync_excel(get_attendance())
                        st.success(f"✅ تم تسجيل حضور {emp.get('full_name')} في {time_str}")
                        st.rerun()
                    else:
                        st.warning(msg)
        
        with tab2:
            _employee_checkin_block(user, today_str)
    
    # ── Employee View ────────────────────────────────────────────────────────
    else:
        st.markdown("### 📋 تسجيل الحضور")
        _employee_checkin_block(user, today_str)

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
        st.metric("📊 Attendance Rate", f"{att_rate}%")
    with c5:
        st.metric("⏰ Late Arrivals", late)
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
            st.download_button("⬇️ Export Attendance CSV",
                               df_show.to_csv(index=False).encode(),
                               "attendance.csv", "text/csv")


def _employee_checkin_block(user, today_str):
    """Shared check-in block with one button."""
    
    # التحقق إذا كان سجل حضور اليوم موجود
    today_records = [a for a in get_attendance(user.get("employee_id"))
                     if a["date"] == today_str]
    
    if today_records:
        r = today_records[0]
        check_in_time = r.get('check_in', '')
        status = r["status"]
        
        badge_class = "badge-present" if status == "Present" else "badge-late"
        status_text = "✅ حاضر" if status == "Present" else "⏰ متأخر"
        
        st.markdown(f"""
        <div class="checkin-status checked">
            <div style="font-size:1.2rem;font-weight:600;color:#E8EAF0;">
                ✅ تم تسجيل حضورك
            </div>
            <div style="color:#C8CADE;font-size:1rem;margin-top:4px;">
                🕐 {check_in_time}
            </div>
            <div style="margin-top:6px;">
                <span class="status-badge {badge_class}">{status_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # زر معطل (ممنوع تسجيل حضور مرتين)
        st.button(
            "✅ تم التسجيل مسبقاً",
            disabled=True,
            use_container_width=True,
            key="checkin_disabled"
        )
    else:
        # زر تسجيل الحضور
        now = datetime.now()
        is_late = now.time() > datetime.strptime("09:15", "%H:%M").time()
        
        if is_late:
            st.warning(f"⏰ متأخر! الوقت الحالي: {now.strftime('%H:%M:%S')} (الحضور المتوقع قبل 9:15)")
        
        if st.button("📍 تسجيل الحضور الآن", key=f"checkin_{user['id']}", use_container_width=True):
            now = datetime.now()
            today_str = now.date().isoformat()
            time_str = now.strftime("%H:%M:%S")
            
            # تحديد الحالة (Late لو بعد 9:15)
            is_late = now.time() > datetime.strptime("09:15", "%H:%M").time()
            status = "Late" if is_late else "Present"
            
            ok, msg = record_attendance(
                user.get("employee_id"),
                user.get("full_name"),
                today_str,
                time_str,
                status
            )
            if ok:
                st.success(f"✅ تم تسجيل حضورك في {time_str}")
                _sync_excel(get_attendance())
                st.rerun()
            else:
                st.warning(msg)
