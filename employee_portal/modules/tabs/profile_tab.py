"""
modules/tabs/profile_tab.py
Profile tab — only admin/leader can edit employee info.
"""

import streamlit as st
from modules.database import (
    get_notes, get_attendance, get_breaks, get_callbacks, update_user
)


def render_profile_tab(user: dict):
    st.markdown("""
    <style>
    .section-head {
        font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:700;
        color:#E8EAF0;margin:1.2rem 0 0.75rem;
        border-left:3px solid #4F6BFF;padding-left:10px;
    }
    .info-grid {
        display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));
        gap:10px;margin-bottom:1rem;
    }
    .info-cell {
        background:#1A1D27;border:1px solid #2E3350;border-radius:12px;
        padding:0.75rem 1rem;
    }
    .info-cell-label { color:#8B90A8;font-size:0.75rem;text-transform:uppercase;
                       letter-spacing:0.05em; }
    .info-cell-val   { color:#E8EAF0;font-size:0.95rem;font-weight:500;margin-top:2px; }
    .act-item {
        display:flex;gap:10px;align-items:flex-start;
        padding:0.6rem 0;border-bottom:1px solid #2E3350;
    }
    .act-dot { width:8px;height:8px;border-radius:50%;background:#4F6BFF;
               margin-top:5px;flex-shrink:0; }
    .act-text { color:#C8CADE;font-size:0.85rem; }
    .act-time { color:#8B90A8;font-size:0.75rem; }
    .readonly-notice {
        background:rgba(79,107,255,0.08);border:1px solid rgba(79,107,255,0.25);
        border-radius:10px;padding:0.65rem 1rem;color:#8B90A8;font-size:0.83rem;
        margin-bottom:1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    is_admin = user["role"] in ("admin", "leader")

    # ── Edit form — admin/leader only ─────────────────────────────────────────
    if is_admin:
        with st.expander("✏️ Edit Profile Information", expanded=False):
            with st.form("edit_profile_form"):
                c1, c2 = st.columns(2)
                with c1:
                    fn  = st.text_input("Full Name",   value=user.get("full_name",""))
                    dep = st.text_input("Department",  value=user.get("department",""))
                    em  = st.text_input("Email",       value=user.get("email",""))
                with c2:
                    pos = st.text_input("Position",    value=user.get("position",""))
                    ph  = st.text_input("Phone",       value=user.get("phone",""))
                    hd  = st.text_input("Hire Date (YYYY-MM-DD)", value=user.get("hire_date",""))
                if st.form_submit_button("💾 Save Changes"):
                    update_user(user["id"],
                                full_name=fn, department=dep, position=pos,
                                email=em, phone=ph, hire_date=hd)
                    st.success("Profile updated!")
                    st.session_state.user.update(
                        full_name=fn, department=dep, position=pos,
                        email=em, phone=ph, hire_date=hd)
                    st.rerun()
    else:
        st.markdown("""
        <div class="readonly-notice">
            🔒 Profile information can only be edited by a Leader or Admin.
            Contact your team leader to update your details.
        </div>
        """, unsafe_allow_html=True)

    # ── Full info grid ────────────────────────────────────────────────────────
    st.markdown('<div class="section-head">Employee Information</div>', unsafe_allow_html=True)
    fields = [
        ("Full Name",    user.get("full_name","—")),
        ("Employee ID",  user.get("employee_id","—")),
        ("Department",   user.get("department","—")),
        ("Position",     user.get("position","—")),
        ("Email",        user.get("email","—")),
        ("Phone",        user.get("phone","—")),
        ("Hire Date",    user.get("hire_date","—")),
        ("Role",         user.get("role","—").capitalize()),
        ("Username",     user.get("username","—")),
    ]
    grid_html = '<div class="info-grid">'
    for label, val in fields:
        grid_html += f"""
        <div class="info-cell">
            <div class="info-cell-label">{label}</div>
            <div class="info-cell-val">{val}</div>
        </div>"""
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

    # ── Stats summary ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-head">Summary Statistics</div>', unsafe_allow_html=True)
    att  = get_attendance(user.get("employee_id"))
    brks = get_breaks(user.get("employee_id"))
    cbs  = get_callbacks(user.get("employee_id"))

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Check-ins",     len(att))
    with c2: st.metric("Total Breaks",        len([b for b in brks if b.get("duration")]))
    with c3: st.metric("Total Callbacks",     len(cbs))
    with c4: st.metric("Completed Callbacks", sum(1 for c in cbs if c["status"]=="Completed"))

    # ── Recent activity ───────────────────────────────────────────────────────
    st.markdown('<div class="section-head">Recent Activity</div>', unsafe_allow_html=True)
    activity = []
    for a in att[:5]:
        activity.append((a.get("date",""), f"✅ Checked in at {a.get('check_in','')}"))
    for b in brks[:5]:
        if b.get("end_time"):
            activity.append((b.get("date",""),
                f"☕ Completed {b.get('break_name','')} — {b.get('duration',0):.0f} min"))
    for c in cbs[:5]:
        activity.append((c.get("callback_date",""),
            f"📞 Callback with {c.get('customer_name','')} — {c.get('status','')}"))

    activity.sort(key=lambda x: x[0], reverse=True)
    if activity:
        for ts, text in activity[:8]:
            st.markdown(f"""
            <div class="act-item">
                <div class="act-dot"></div>
                <div>
                    <div class="act-text">{text}</div>
                    <div class="act-time">{ts}</div>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No recent activity.")

    # ── Latest notes ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-head">Latest Notes From Leader</div>', unsafe_allow_html=True)
    notes = get_notes(user.get("employee_id"))[:3]
    if notes:
        for n in notes:
            st.markdown(f"""
            <div style="background:#1A1D27;border:1px solid #2E3350;border-radius:12px;
                        padding:0.75rem 1rem;margin-bottom:0.5rem">
                <span style="color:#4F6BFF;font-weight:600;font-size:0.82rem">
                    ✍️ {n['author']}</span>
                <span style="color:#8B90A8;font-size:0.75rem;margin-left:8px">
                    {n.get('created_at','')[:16]}</span>
                <div style="color:#C8CADE;font-size:0.87rem;margin-top:4px">
                    {n['note']}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No notes from leader yet.")
