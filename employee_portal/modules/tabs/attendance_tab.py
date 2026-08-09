"""
modules/tabs/attendance_tab.py
Attendance tab — QR per employee (admin can generate for any), check-in, charts.
"""

import streamlit as st
import pandas as pd
import os, io, base64, json
from datetime import date, datetime, timedelta
from modules.database import record_attendance, get_attendance, get_all_users

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
ATT_FILE = os.path.join(DATA_DIR, "attendance.xlsx")


def _sync_excel(records):
    os.makedirs(DATA_DIR, exist_ok=True)
    pd.DataFrame(records).to_excel(ATT_FILE, index=False)


def _generate_qr(employee_id: str, full_name: str) -> bytes | None:
    try:
        import qrcode
        payload = json.dumps({
            "employee_id": employee_id,
            "full_name":   full_name,
            "date":        date.today().isoformat(),
        })
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#4F6BFF", back_color="#1A1D27")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        return None


def _qr_card(employee_id, full_name, label=""):
    """Render a QR card for one employee."""
    qr_bytes = _generate_qr(employee_id, full_name)
    st.markdown(f"""
    <div style="background:#1A1D27;border:1px solid #2E3350;border-radius:14px;
                padding:1rem;text-align:center;margin-bottom:0.5rem">
        <div style="font-weight:600;color:#E8EAF0;margin-bottom:4px">{label or full_name}</div>
        <div style="color:#8B90A8;font-size:0.78rem;margin-bottom:0.75rem">{employee_id}</div>
    """, unsafe_allow_html=True)
    if qr_bytes:
        b64 = base64.b64encode(qr_bytes).decode()
        st.markdown(f"""
        <img src="data:image/png;base64,{b64}"
             style="width:160px;height:160px;border-radius:10px"/>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.download_button(f"⬇️ Download QR",
                           qr_bytes,
                           f"qr_{employee_id}_{date.today()}.png",
                           "image/png",
                           key=f"dl_qr_{employee_id}")
    else:
        st.markdown('</div>', unsafe_allow_html=True)
        st.warning("Install qrcode: `pip install qrcode pillow`")


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
    </style>
    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # ADMIN VIEW — Generate QR for any employee
    # ═══════════════════════════════════════════════════════════════════════════
    if is_admin:
        st.markdown("### 🛡️ Admin — Generate QR Codes for Employees")
        employees = [e for e in get_all_users() if e["role"] == "employee"]

        sub1, sub2 = st.tabs(["📱 Generate QR Codes", "✅ My Own Check-In"])

        with sub1:
            if not employees:
                st.info("No employees found.")
            else:
                # Filter
                search_emp = st.text_input("🔍 Search employee", key="att_admin_search")
                filtered_emps = [e for e in employees
                                 if not search_emp
                                 or search_emp.lower() in (e.get("full_name","") or "").lower()
                                 or search_emp.lower() in (e.get("employee_id","") or "").lower()]

                # Show all QRs in a grid
                cols_per_row = 3
                for i in range(0, len(filtered_emps), cols_per_row):
                    row_emps = filtered_emps[i:i+cols_per_row]
                    cols = st.columns(cols_per_row)
                    for j, emp in enumerate(row_emps):
                        with cols[j]:
                            _qr_card(
                                emp.get("employee_id",""),
                                emp.get("full_name",""),
                                label=f"{emp.get('full_name','')} — {emp.get('department','')}"
                            )

                st.markdown("---")
                st.markdown("**Manual attendance entry for any employee:**")
                with st.form("manual_att_admin"):
                    emp_options = {
                        f"{e.get('full_name','')} ({e.get('employee_id','')})": e
                        for e in employees
                    }
                    selected_label = st.selectbox("Select Employee", list(emp_options.keys()),
                                                  key="att_emp_sel")
                    att_dt = st.date_input("Date",  value=date.today())
                    att_tm = st.time_input("Check-In Time")
                    att_st = st.selectbox("Status", ["Present","Late","Absent"])
                    if st.form_submit_button("✅ Add Attendance Record"):
                        emp = emp_options[selected_label]
                        ok, msg = record_attendance(
                            emp.get("employee_id"), emp.get("full_name"),
                            att_dt.isoformat(), att_tm.strftime("%H:%M:%S"), att_st)
                        if ok:
                            _sync_excel(get_attendance())
                            st.success(msg)
                        else:
                            st.warning(msg)

        with sub2:
            _employee_checkin_block(user, today_str)

    # ═══════════════════════════════════════════════════════════════════════════
    # EMPLOYEE VIEW
    # ═══════════════════════════════════════════════════════════════════════════
    else:
        col_qr, col_scan = st.columns([1,1], gap="large")
        with col_qr:
            st.markdown('<div class="att-card">', unsafe_allow_html=True)
            st.markdown("#### 📱 Your Attendance QR Code")
            st.markdown(f"**{user.get('full_name','')}** — {today_str}")
            _qr_card(user.get("employee_id",""), user.get("full_name",""))
            st.markdown('</div>', unsafe_allow_html=True)
        with col_scan:
            st.markdown('<div class="att-card">', unsafe_allow_html=True)
            _employee_checkin_block(user, today_str)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    # ── Metrics ───────────────────────────────────────────────────────────────
    records   = get_attendance(None if is_admin else user.get("employee_id"))
    today_obj = date.today()
    week_start  = today_obj - timedelta(days=today_obj.weekday())
    month_start = today_obj.replace(day=1)

    today_cnt = sum(1 for r in records if r["date"] == today_str)
    week_cnt  = sum(1 for r in records if r["date"] >= week_start.isoformat())
    month_cnt = sum(1 for r in records if r["date"] >= month_start.isoformat())
    total     = len(records)
    present   = sum(1 for r in records if r["status"]=="Present")
    late      = sum(1 for r in records if r["status"]=="Late")
    att_rate  = round(present/total*100) if total else 0

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: st.metric("Today",           today_cnt)
    with c2: st.metric("This Week",       week_cnt)
    with c3: st.metric("This Month",      month_cnt)
    with c4: st.metric("Attendance Rate", f"{att_rate}%")
    with c5: st.metric("Late Arrivals",   late)
    with c6: st.metric("Absent",          total - present - late)

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
                fig.update_layout(paper_bgcolor="#1A1D27",plot_bgcolor="#1A1D27",
                                  font_color="#C8CADE",margin=dict(l=10,r=10,t=40,b=10),
                                  title_font_size=13)
                st.plotly_chart(fig, use_container_width=True)
            with col_r:
                sc = df["status"].value_counts().reset_index()
                sc.columns = ["Status","Count"]
                fig2 = px.pie(sc, values="Count", names="Status",
                              title="Status Distribution", template="plotly_dark",
                              color_discrete_sequence=["#06D6A0","#FFD166","#FF6B6B"])
                fig2.update_layout(paper_bgcolor="#1A1D27",font_color="#C8CADE",
                                   margin=dict(l=10,r=10,t=40,b=10),title_font_size=13)
                st.plotly_chart(fig2, use_container_width=True)
    except ImportError:
        pass

    # ── Table ─────────────────────────────────────────────────────────────────
    st.markdown("#### Attendance Records")
    df_show = pd.DataFrame(records)
    if not df_show.empty:
        show_cols = [c for c in ["employee_id","full_name","date","check_in","status"]
                     if c in df_show.columns]
        st.dataframe(df_show[show_cols], use_container_width=True, height=300)
        if is_admin:
            st.download_button("⬇️ Export Attendance CSV",
                               df_show.to_csv(index=False).encode(),
                               "attendance.csv","text/csv")


def _employee_checkin_block(user, today_str):
    """Shared check-in block for both employee and admin's own check-in."""
    st.markdown("#### ✅ Check In")
    today_records = [a for a in get_attendance(user.get("employee_id"))
                     if a["date"] == today_str]
    if today_records:
        r = today_records[0]
        st.success(f"✅ Already checked in today at **{r.get('check_in','')}**")
        badge = "badge-present" if r["status"]=="Present" else "badge-late"
        st.markdown(f'<span class="status-badge {badge}">{r["status"]}</span>',
                    unsafe_allow_html=True)
    else:
        is_late = datetime.now().time() > datetime.strptime("09:15","%H:%M").time()
        status_auto = "Late" if is_late else "Present"
        if is_late:
            st.warning(f"⚠️ Late check-in — {datetime.now().strftime('%H:%M:%S')}")
        if st.button("📍 Check In Now", key=f"checkin_{user['id']}", use_container_width=True):
            ok, msg = record_attendance(
                user.get("employee_id"), user.get("full_name"),
                today_str, datetime.now().strftime("%H:%M:%S"), status_auto)
            if ok:
                st.success(msg)
                _sync_excel(get_attendance())
                st.rerun()
            else:
                st.warning(msg)
