"""
modules/tabs/admin_tab.py
Admin / Leader panel — manage employees, view all data, add notes.
"""

import streamlit as st
import pandas as pd
from modules.database import (
    get_all_users, add_user, update_user, delete_user, reset_password,
    add_note, get_notes, get_attendance, get_breaks, get_callbacks
)


def render_admin_tab(user: dict):
    if user["role"] not in ("admin", "leader"):
        st.error("Access denied.")
        return

    st.markdown("""
    <style>
    .admin-section {
        background:#1A1D27;border:1px solid #2E3350;border-radius:14px;
        padding:1.25rem;margin-bottom:1rem;
    }
    .sec-title {
        font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:700;
        color:#E8EAF0;margin-bottom:1rem;border-left:3px solid #7C3AED;
        padding-left:10px;
    }
    </style>
    """, unsafe_allow_html=True)

    admin_tabs = st.tabs([
        "👥 Employees", "➕ Add Employee", "📋 All Attendance",
        "☕ All Breaks",  "📞 All Callbacks", "📝 Add Note"
    ])

    t_emp, t_add, t_att, t_brk, t_cb, t_note = admin_tabs

    # ── Employees ─────────────────────────────────────────────────────────────
    with t_emp:
        st.markdown('<div class="sec-title">All Employees</div>', unsafe_allow_html=True)
        employees = get_all_users()

        search = st.text_input("🔍 Search employees", key="adm_emp_search")
        if search:
            employees = [e for e in employees
                         if search.lower() in (e.get("full_name","") or "").lower()
                         or search.lower() in (e.get("employee_id","") or "").lower()
                         or search.lower() in (e.get("department","") or "").lower()]

        for emp in employees:
            with st.expander(
                f"{emp.get('full_name','—')} [{emp.get('employee_id','—')}] — {emp.get('role','').capitalize()}",
                expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    new_name = st.text_input("Full Name", value=emp.get("full_name",""),
                                             key=f"fn_{emp['id']}")
                    new_dept = st.text_input("Department", value=emp.get("department",""),
                                             key=f"dep_{emp['id']}")
                    new_pos  = st.text_input("Position", value=emp.get("position",""),
                                             key=f"pos_{emp['id']}")
                with c2:
                    new_em  = st.text_input("Email", value=emp.get("email",""),
                                            key=f"em_{emp['id']}")
                    new_ph  = st.text_input("Phone", value=emp.get("phone",""),
                                            key=f"ph_{emp['id']}")
                    new_hd  = st.text_input("Hire Date", value=emp.get("hire_date",""),
                                            key=f"hd_{emp['id']}")

                col_save, col_del, col_pw = st.columns(3)
                with col_save:
                    if st.button("💾 Save", key=f"adm_save_{emp['id']}"):
                        update_user(emp["id"], full_name=new_name, department=new_dept,
                                    position=new_pos, email=new_em,
                                    phone=new_ph, hire_date=new_hd)
                        st.success("Updated!")
                        st.rerun()
                with col_del:
                    if st.button("🗑️ Delete", key=f"adm_del_{emp['id']}"):
                        delete_user(emp["id"])
                        st.warning("Employee deactivated.")
                        st.rerun()
                with col_pw:
                    new_pw = st.text_input("New Password", type="password",
                                           key=f"pw_{emp['id']}")
                    if st.button("🔑 Reset PW", key=f"adm_rpw_{emp['id']}"):
                        if new_pw:
                            reset_password(emp["id"], new_pw)
                            st.success("Password reset!")
                        else:
                            st.warning("Enter new password first.")

    # ── Add Employee ──────────────────────────────────────────────────────────
    with t_add:
        st.markdown('<div class="sec-title">Add New Employee</div>', unsafe_allow_html=True)
        with st.form("add_emp_form"):
            c1, c2 = st.columns(2)
            with c1:
                u_user = st.text_input("Username *")
                u_pw   = st.text_input("Password *", type="password")
                u_role = st.selectbox("Role", ["employee","leader","admin"])
                u_name = st.text_input("Full Name *")
                u_eid  = st.text_input("Employee ID *")
            with c2:
                u_dept = st.text_input("Department")
                u_pos  = st.text_input("Position")
                u_em   = st.text_input("Email")
                u_ph   = st.text_input("Phone")
                u_hd   = st.text_input("Hire Date (YYYY-MM-DD)")

            if st.form_submit_button("➕ Create Employee"):
                if not u_user or not u_pw or not u_name or not u_eid:
                    st.error("Username, Password, Full Name, Employee ID are required.")
                else:
                    ok, msg = add_user(u_user, u_pw, u_role, u_name, u_eid,
                                       u_dept, u_pos, u_em, u_ph, u_hd)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(f"Failed: {msg}")

    # ── All Attendance ────────────────────────────────────────────────────────
    with t_att:
        st.markdown('<div class="sec-title">All Attendance Records</div>', unsafe_allow_html=True)
        records = get_attendance()
        if records:
            df = pd.DataFrame(records)
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button("⬇️ Export CSV", df.to_csv(index=False).encode(),
                               "all_attendance.csv")
        else:
            st.info("No attendance records yet.")

    # ── All Breaks ────────────────────────────────────────────────────────────
    with t_brk:
        st.markdown('<div class="sec-title">All Break Records</div>', unsafe_allow_html=True)
        records = get_breaks()
        if records:
            df = pd.DataFrame(records)
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button("⬇️ Export CSV", df.to_csv(index=False).encode(),
                               "all_breaks.csv")
        else:
            st.info("No break records yet.")

    # ── All Callbacks ─────────────────────────────────────────────────────────
    with t_cb:
        st.markdown('<div class="sec-title">All Callbacks</div>', unsafe_allow_html=True)
        records = get_callbacks()
        if records:
            df = pd.DataFrame(records)
            st.dataframe(df, use_container_width=True, height=400)
            st.download_button("⬇️ Export CSV", df.to_csv(index=False).encode(),
                               "all_callbacks.csv")
        else:
            st.info("No callbacks yet.")

    # ── Add Note ──────────────────────────────────────────────────────────────
    with t_note:
        st.markdown('<div class="sec-title">Add Note to Employee</div>', unsafe_allow_html=True)
        employees = get_all_users()
        emp_options = {
            f"{e.get('full_name','?')} ({e.get('employee_id','?')})": e.get("employee_id")
            for e in employees if e["role"] == "employee"
        }
        if not emp_options:
            st.info("No employees found.")
        else:
            selected = st.selectbox("Select Employee", list(emp_options.keys()),
                                    key="note_emp_sel")
            note_text = st.text_area("Note Content", height=120, key="adm_note_text")
            if st.button("📌 Add Note", key="adm_add_note"):
                if note_text.strip():
                    add_note(emp_options[selected],
                             user.get("full_name","Admin"), note_text.strip())
                    st.success("Note added!")
                else:
                    st.warning("Note cannot be empty.")

            # Show existing notes for selected employee
            if selected:
                emp_id = emp_options[selected]
                notes = get_notes(emp_id)
                if notes:
                    st.markdown("**Existing Notes:**")
                    for n in notes:
                        st.markdown(f"""
                        <div style="background:#0F1117;border:1px solid #2E3350;
                                    border-radius:10px;padding:0.7rem 1rem;
                                    margin-bottom:0.5rem">
                            <span style="color:#4F6BFF;font-weight:600;font-size:0.8rem">
                                ✍️ {n['author']}</span>
                            <span style="color:#8B90A8;font-size:0.75rem;margin-left:8px">
                                {n.get('created_at','')[:16]}</span>
                            <div style="color:#C8CADE;font-size:0.85rem;margin-top:4px">
                                {n['note']}</div>
                        </div>""", unsafe_allow_html=True)
