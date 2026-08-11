"""
modules/tabs/admin_tab.py
"""

import streamlit as st
import pandas as pd
from modules.database import (
    get_all_users, add_user, update_user, delete_user, reset_password,
    add_note, get_notes, get_attendance, get_breaks, get_callbacks
)
from modules.backup_utils import create_backup, get_backup_list, restore_backup

_P = "admintab_"


def render_admin_tab(user: dict):
    if user["role"] not in ("admin", "leader"):
        st.error("Access denied.")
        return

    st.markdown("""
    <style>
    .sec-title {
        font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:700;
        color:#E8EAF0;margin-bottom:1rem;border-left:3px solid #7C3AED;
        padding-left:10px;
    }
    .backup-card {
        background: #1A1D27;
        border: 1px solid #2E3350;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    selected = st.radio(
        "Admin Section",
        ["👥 Employees", "➕ Add Employee", "📋 All Attendance",
         "☕ All Breaks", "📞 All Callbacks", "📝 Add Note", 
         "💾 Backup & Restore", "☁️ Google Drive Backup"],
        horizontal=True,
        label_visibility="collapsed",
        key=f"{_P}nav"
    )

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    if selected == "👥 Employees":
        render_employees_section()
    elif selected == "➕ Add Employee":
        render_add_employee_section()
    elif selected == "📋 All Attendance":
        render_all_attendance_section()
    elif selected == "☕ All Breaks":
        render_all_breaks_section()
    elif selected == "📞 All Callbacks":
        render_all_callbacks_section()
    elif selected == "📝 Add Note":
        render_add_note_section(user)
    elif selected == "💾 Backup & Restore":
        render_backup_restore_section()
    elif selected == "☁️ Google Drive Backup":
        render_google_drive_backup_section()


def render_employees_section():
    st.markdown('<div class="sec-title">All Employees</div>', unsafe_allow_html=True)
    employees = get_all_users()
    search = st.text_input("🔍 Search", key=f"{_P}emp_search")
    if search:
        employees = [e for e in employees
                     if search.lower() in (e.get("full_name","") or "").lower()
                     or search.lower() in (e.get("employee_id","") or "").lower()
                     or search.lower() in (e.get("department","") or "").lower()]
    seen = set()
    for idx, emp in enumerate(employees):
        uid = emp.get('id', idx)
        if uid in seen:
            continue
        seen.add(uid)
        k = f"{_P}{uid}_{idx}"
        with st.expander(
            f"{emp.get('full_name','—')} [{emp.get('employee_id','—')}] — {emp.get('role','').capitalize()}",
            expanded=False
        ):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("Full Name",  value=emp.get("full_name",""),  key=f"{k}_fn")
                new_dept = st.text_input("Department", value=emp.get("department",""), key=f"{k}_dep")
                new_pos  = st.text_input("Position",   value=emp.get("position",""),   key=f"{k}_pos")
            with c2:
                new_em = st.text_input("Email",     value=emp.get("email",""),     key=f"{k}_em")
                new_ph = st.text_input("Phone",     value=emp.get("phone",""),     key=f"{k}_ph")
                new_hd = st.text_input("Hire Date", value=emp.get("hire_date",""), key=f"{k}_hd")
            col_save, col_del, col_pw = st.columns(3)
            with col_save:
                if st.button("💾 Save", key=f"{k}_save"):
                    update_user(emp['id'], full_name=new_name, department=new_dept,
                                position=new_pos, email=new_em, phone=new_ph, hire_date=new_hd)
                    st.success("Updated!")
                    st.rerun()
            with col_del:
                if st.button("🗑️ Delete", key=f"{k}_del"):
                    delete_user(emp['id'])
                    st.warning("Deactivated.")
                    st.rerun()
            with col_pw:
                new_pw = st.text_input("New Password", type="password", key=f"{k}_pw")
                if st.button("🔑 Reset PW", key=f"reset_pw_{emp['id']}"):
                    if new_pw:
                        reset_password(emp['id'], new_pw)
                        st.success("Password reset!")
                    else:
                        st.warning("Enter new password first.")


def render_add_employee_section():
    st.markdown('<div class="sec-title">Add New Employee</div>', unsafe_allow_html=True)
    with st.form(f"{_P}add_emp_form"):
        c1, c2 = st.columns(2)
        with c1:
            u_user = st.text_input("Username *")
            u_pw   = st.text_input("Password *", type="password")
            u_role = st.selectbox("Role", ["employee", "leader", "admin"])
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
                    st.rerun()
                else:
                    st.error(f"Failed: {msg}")


def render_all_attendance_section():
    st.markdown('<div class="sec-title">All Attendance Records</div>', unsafe_allow_html=True)
    records = get_attendance()
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True, height=400)
        st.download_button("⬇️ Export CSV", df.to_csv(index=False).encode(),
                           "all_attendance.csv", key=f"{_P}dl_att")
    else:
        st.info("No attendance records yet.")


def render_all_breaks_section():
    st.markdown('<div class="sec-title">All Break Records</div>', unsafe_allow_html=True)
    records = get_breaks()
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True, height=400)
        st.download_button("⬇️ Export CSV", df.to_csv(index=False).encode(),
                           "all_breaks.csv", key=f"{_P}dl_brk")
    else:
        st.info("No break records yet.")


def render_all_callbacks_section():
    st.markdown('<div class="sec-title">All Callbacks</div>', unsafe_allow_html=True)
    records = get_callbacks()
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True, height=400)
        st.download_button("⬇️ Export CSV", df.to_csv(index=False).encode(),
                           "all_callbacks.csv", key=f"{_P}dl_cb")
    else:
        st.info("No callbacks yet.")


def render_add_note_section(user):
    st.markdown('<div class="sec-title">Add Note to Employee</div>', unsafe_allow_html=True)
    employees = get_all_users()
    emp_options = {
        f"{e.get('full_name','?')} ({e.get('employee_id','?')})": e.get("employee_id")
        for e in employees if e["role"] == "employee"
    }
    if not emp_options:
        st.info("No employees found.")
    else:
        sel_emp = st.selectbox("Select Employee", list(emp_options.keys()),
                               key=f"{_P}note_emp_sel")
        note_text = st.text_area("Note Content", height=120, key=f"{_P}note_text")
        if st.button("📌 Add Note", key=f"{_P}add_note_btn"):
            if note_text.strip():
                add_note(emp_options[sel_emp], user.get("full_name","Admin"), note_text.strip())
                st.success("Note added!")
                st.rerun()
            else:
                st.warning("Note cannot be empty.")
        if sel_emp:
            notes = get_notes(emp_options[sel_emp])
            if notes:
                st.markdown("**Existing Notes:**")
                for n in notes:
                    st.markdown(f"""
                    <div style="background:#0F1117;border:1px solid #2E3350;
                                border-radius:10px;padding:0.7rem 1rem;margin-bottom:0.5rem">
                        <span style="color:#4F6BFF;font-weight:600;font-size:0.8rem">
                            ✍️ {n['author']}</span>
                        <span style="color:#8B90A8;font-size:0.75rem;margin-left:8px">
                            {n.get('created_at','')[:16]}</span>
                        <div style="color:#C8CADE;font-size:0.85rem;margin-top:4px">
                            {n['note']}</div>
                    </div>""", unsafe_allow_html=True)


def render_backup_restore_section():
    """Render backup and restore section."""
    st.markdown('<div class="sec-title">💾 Backup & Restore</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📥 Create Backup")
        if st.button("🔄 Create Local Backup", use_container_width=True):
            with st.spinner("Creating backup..."):
                success, msg, link = create_backup(upload_to_drive_flag=False)
                if success:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")
    
    with col2:
        st.markdown("#### 📤 Restore from Backup")
        backups = get_backup_list()
        if backups:
            backup_options = [b["filename"] for b in backups]
            selected_backup = st.selectbox("Select backup to restore", backup_options)
            
            if st.button("⚠️ Restore Selected Backup", use_container_width=True, type="secondary"):
                confirm = st.checkbox("⚠️ I understand this will replace the current database")
                if confirm:
                    success, msg = restore_backup(selected_backup)
                    if success:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.warning("Please confirm to proceed.")
        else:
            st.info("No local backups available.")
    
    # ── Show backup list ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📋 Available Local Backups")
    
    backups = get_backup_list()
    if backups:
        df = pd.DataFrame(backups)
        st.dataframe(df[["filename", "size", "created"]], use_container_width=True)
        
        st.markdown("#### ⬇️ Download Backup File")
        selected_download = st.selectbox("Select backup to download", [b["filename"] for b in backups])
        if selected_download:
            import os
            backup_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "backups", selected_download)
            if os.path.exists(backup_path):
                with open(backup_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Selected Backup",
                        data=f.read(),
                        file_name=selected_download,
                        mime="application/octet-stream"
                    )
    else:
        st.info("No backups found. Create one first!")


def render_google_drive_backup_section():
    """Render Google Drive backup section."""
    st.markdown('<div class="sec-title">☁️ Google Drive Backup</div>', unsafe_allow_html=True)
    
    # Check configuration
    web_app_url = st.secrets.get("drive_apps_script", {}).get("web_app_url", None)
    folder_id = st.secrets.get("drive_apps_script", {}).get("folder_id", None)
    
    if not web_app_url:
        st.warning("""
        ⚠️ Google Drive backup is not configured.
        
        Please add to `.streamlit/secrets.toml`:
        
        ```toml
        [drive_apps_script]
        web_app_url = "https://script.google.com/macros/s/your-script-id/exec"
        folder_id = "your-google-drive-folder-id"  # optional
