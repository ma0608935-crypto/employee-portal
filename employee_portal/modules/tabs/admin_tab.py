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


# ... باقي الدوال (employees, add employee, attendance, breaks, callbacks, add note) ...

# ── Backup & Restore ──────────────────────────────────────────────────────────

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
    
    # Check if secrets exist
    try:
        web_app_url = st.secrets.get("drive_apps_script", {}).get("web_app_url", None)
        folder_id = st.secrets.get("drive_apps_script", {}).get("folder_id", None)
    except:
        web_app_url = None
        folder_id = None
    
    if not web_app_url:
        st.warning("""
        ⚠️ Google Drive backup is not configured.
        
        Please add to `.streamlit/secrets.toml`:
        
        ```toml
        [drive_apps_script]
        web_app_url = "https://script.google.com/macros/s/your-script-id/exec"
        folder_id = "your-google-drive-folder-id"  # optional
