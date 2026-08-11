"""
modules/components.py
Reusable UI components: profile card, notes panel, performance dashboard.
"""

import streamlit as st
import os, base64
from datetime import datetime, date, timedelta
from modules.database import (
    get_notes, add_note, update_user,
    get_attendance, get_breaks, get_callbacks
)

PHOTO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "photos")


def _load_photo(path):
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


def profile_card(user: dict):
    """Left-side employee profile card."""
    
    # Initialize session state for showing upload
    upload_key = f"show_upload_{user['id']}"
    if upload_key not in st.session_state:
        st.session_state[upload_key] = False

    st.markdown("""
    <style>
    .pcard {
        background: #1A1D27;
        border: 1px solid #2E3350;
        border-radius: 18px;
        padding: 1.2rem 1.5rem;
        display: flex;
        gap: 1.5rem;
        align-items: flex-start;
    }
    .pcard-avatar-section {
        flex-shrink: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .pcard-info-section {
        flex: 1;
        padding-top: 0.2rem;
    }
    .pcard-name {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.4rem;
        font-weight: 700;
        color: #E8EAF0;
        margin: 0 0 0.1rem 0;
    }
    .pcard-pos {
        color: #8B90A8;
        font-size: 0.9rem;
        margin-bottom: 0.8rem;
    }
    .pcard-info {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .pcard-row {
        display: flex;
        gap: 8px;
        font-size: 0.85rem;
        align-items: baseline;
    }
    .pcard-label {
        color: #8B90A8;
        min-width: 100px;
    }
    .pcard-val {
        color: #C8CADE;
        font-weight: 500;
    }
    
    /* ===== Avatar ===== */
    .avatar-wrapper {
        position: relative;
        display: inline-block;
        width: 150px;
        height: 150px;
    }
    .avatar-wrapper img {
        width: 150px;
        height: 150px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #2E3350;
    }
    .avatar-wrapper .avatar-initials {
        width: 150px;
        height: 150px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4F6BFF, #7C3AED);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3.5rem;
        font-weight: 700;
        color: white;
        border: 3px solid #2E3350;
    }
    .avatar-edit-btn {
        margin-top: 6px;
        background: transparent;
        color: #8B90A8;
        border: 1px solid #2E3350;
        border-radius: 8px;
        padding: 2px 12px;
        font-size: 0.7rem;
        cursor: pointer;
        transition: all 0.2s;
        width: 100%;
        text-align: center;
    }
    .avatar-edit-btn:hover {
        background: #2E3350;
        color: #E8EAF0;
    }
    
    /* Upload area */
    .upload-area {
        margin-top: 6px;
        padding: 8px 10px;
        background: #0F1117;
        border: 1px solid #2E3350;
        border-radius: 8px;
        width: 100%;
    }
    .upload-area p {
        color: #8B90A8;
        font-size: 0.7rem;
        margin: 0 0 4px 0;
        text-align: center;
    }
    .upload-area .remove-btn {
        background: transparent;
        color: #FF6B6B;
        border: 1px solid #FF6B6B44;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.7rem;
        cursor: pointer;
        transition: all 0.2s;
        margin-top: 4px;
        width: 100%;
    }
    .upload-area .remove-btn:hover {
        background: #FF6B6B22;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Card Container (flex row) ──────────────────────────────────────────
    st.markdown('<div class="pcard">', unsafe_allow_html=True)
    
    # ── Avatar Section ───────────────────────────────────────────────────────
    photo_b64 = _load_photo(user.get("photo_path"))
    
    st.markdown('<div class="pcard-avatar-section">', unsafe_allow_html=True)
    
    # Display avatar
    if photo_b64:
        st.markdown(f'''
        <div class="avatar-wrapper">
            <img src="data:image/jpeg;base64,{photo_b64}" alt="Profile Photo">
        </div>
        ''', unsafe_allow_html=True)
    else:
        initials = "".join(p[0].upper() for p in (user.get("full_name") or "U").split()[:2])
        st.markdown(f'''
        <div class="avatar-wrapper">
            <div class="avatar-initials">{initials}</div>
        </div>
        ''', unsafe_allow_html=True)
    
    # Edit button (pencil icon)
    if st.button("🖊️ Edit Photo", key=f"edit_photo_{user['id']}", help="Change photo"):
        st.session_state[upload_key] = not st.session_state[upload_key]
        st.rerun()
    
    # ── Upload area (shown only when session state is True) ────────────────
    if st.session_state[upload_key]:
        st.markdown('<div class="upload-area">', unsafe_allow_html=True)
        st.markdown('<p>📸 Upload new photo</p>', unsafe_allow_html=True)
        
        uploaded = st.file_uploader(
            "Choose a photo...",
            type=["jpg", "jpeg", "png"],
            key=f"photo_up_{user['id']}",
            label_visibility="collapsed",
            accept_multiple_files=False
        )
        
        if uploaded:
            os.makedirs(PHOTO_DIR, exist_ok=True)
            ext = uploaded.name.rsplit(".", 1)[-1]
            path = os.path.join(PHOTO_DIR, f"{user['employee_id']}.{ext}")
            with open(path, "wb") as f:
                f.write(uploaded.read())
            update_user(user["id"], photo_path=path)
            st.session_state.user["photo_path"] = path
            st.session_state[upload_key] = False
            st.rerun()

        # Remove photo button (only if photo exists)
        if user.get("photo_path") and os.path.exists(user["photo_path"]):
            if st.button("🗑️ Remove Photo", key=f"del_photo_{user['id']}"):
                try:
                    os.remove(user["photo_path"])
                except:
                    pass
                update_user(user["id"], photo_path=None)
                st.session_state.user["photo_path"] = None
                st.session_state[upload_key] = False
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # end avatar-section

    # ── Info Section ────────────────────────────────────────────────────────
    st.markdown('<div class="pcard-info-section">', unsafe_allow_html=True)
    
    dept = user.get("department", "—")
    pos = user.get("position", "—")
    
    st.markdown(f"""
    <div class="pcard-name">{user.get('full_name','—')}</div>
    <div class="pcard-pos">{pos} · {dept}</div>
    <div class="pcard-info">
        <div class="pcard-row">
            <span class="pcard-label">🪪 Employee ID</span>
            <span class="pcard-val">{user.get('employee_id','—')}</span>
        </div>
        <div class="pcard-row">
            <span class="pcard-label">📧 Email</span>
            <span class="pcard-val">{user.get('email','—')}</span>
        </div>
        <div class="pcard-row">
            <span class="pcard-label">📱 Phone</span>
            <span class="pcard-val">{user.get('phone','—')}</span>
        </div>
        <div class="pcard-row">
            <span class="pcard-label">📅 Hired</span>
            <span class="pcard-val">{user.get('hire_date','—')}</span>
        </div>
        <div class="pcard-row">
            <span class="pcard-label">🏢 Role</span>
            <span class="pcard-val" style="text-transform:capitalize">
                {user.get('role','—')}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # end info-section
    st.markdown('</div>', unsafe_allow_html=True)  # end pcard


def notes_panel(user: dict):
    """Right-side leader notes panel."""
    st.markdown("""
    <style>
    .notes-panel {
        background: #1A1D27;
        border: 1px solid #2E3350;
        border-radius: 18px;
        padding: 1.25rem;
        height: 100%;
    }
    .notes-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1rem;
        font-weight: 700;
        color: #E8EAF0;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 1rem;
    }
    .note-item {
        background: #0F1117;
        border: 1px solid #2E3350;
        border-radius: 12px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.6rem;
    }
    .note-author { color: #4F6BFF; font-weight: 600; font-size: 0.8rem; }
    .note-ts     { color: #8B90A8; font-size: 0.72rem; margin-left: 6px; }
    .note-text   { color: #C8CADE; font-size: 0.85rem; margin-top: 4px; line-height: 1.5; }
    .no-notes    { color: #8B90A8; font-size: 0.85rem; text-align: center; padding: 1.5rem 0; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="notes-panel">', unsafe_allow_html=True)
    st.markdown('<div class="notes-title">📝 Notes From Leader</div>', unsafe_allow_html=True)

    is_leader = user["role"] in ("admin", "leader")

    # Add note form (leaders/admins only)
    if is_leader:
        target_emp = user.get("employee_id")
        new_note = st.text_area("Add a note", placeholder="Write a note for this employee…",
                                key="new_note_input", height=80, label_visibility="collapsed")
        if st.button("📌 Add Note", key="notes_panel_add_btn", use_container_width=True):
            if new_note.strip():
                add_note(target_emp, user.get("full_name", "Leader"), new_note.strip())
                st.success("Note added.")
                st.rerun()
            else:
                st.warning("Note cannot be empty.")

    # Display notes
    notes = get_notes(user.get("employee_id"))
    if notes:
        for n in notes:
            ts = n.get("created_at", "")[:16]
            st.markdown(f"""
            <div class="note-item">
                <span class="note-author">✍️ {n['author']}</span>
                <span class="note-ts">{ts}</span>
                <div class="note-text">{n['note']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-notes">No notes yet.</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def performance_dashboard(user: dict):
    """Compact KPI summary bar above the tabs."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    attendance = get_attendance(user.get("employee_id"))
    breaks_data = get_breaks(user.get("employee_id"))
    callbacks  = get_callbacks(user.get("employee_id"))

    # Attendance metrics
    total_days  = len(attendance)
    present     = sum(1 for a in attendance if a["status"] == "Present")
    att_rate    = round(present / total_days * 100) if total_days else 0

    # Break metrics
    completed_breaks = [b for b in breaks_data if b.get("duration")]
    total_break_min  = sum(b["duration"] for b in completed_breaks)

    # Callback metrics
    total_cb     = len(callbacks)
    completed_cb = sum(1 for c in callbacks if c["status"] == "Completed")
    pending_cb   = sum(1 for c in callbacks if c["status"] == "Pending")

    st.markdown("""
    <div style="background:#1A1D27;border:1px solid #2E3350;border-radius:16px;
                padding:1rem 1.25rem;margin-bottom:0">
        <div style="font-family:'Space Grotesk',sans-serif;font-size:0.85rem;
                    font-weight:600;color:#8B90A8;text-transform:uppercase;
                    letter-spacing:0.06em;margin-bottom:0.8rem">
            📊 Performance Dashboard
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    with c1:
        st.metric("Attendance Rate", f"{att_rate}%",
                  delta=f"+{present} days" if present else None)
    with c2:
        absent = total_days - present
        st.metric("Absences", absent)
    with c3:
        late = sum(1 for a in attendance
                   if a.get("check_in") and a["check_in"] > "09:15")
        st.metric("Late Arrivals", late)
    with c4:
        st.metric("Break Time", f"{int(total_break_min)}m")
    with c5:
        st.metric("Total Callbacks", total_cb)
    with c6:
        st.metric("Completed CBs", completed_cb)
    with c7:
        st.metric("Pending CBs", pending_cb)
