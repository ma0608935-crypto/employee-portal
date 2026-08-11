"""
modules/tabs/messages_tab.py
Internal messaging system for employees, admins, and leaders.
"""

import streamlit as st
from datetime import datetime
from modules.database import (
    get_all_users, get_employee, send_message, get_messages_for_user,
    get_unread_count, mark_message_as_read, delete_message, get_conversation
)


def render_messages_tab(user: dict):
    """Render the messages tab."""
    is_admin = user["role"] in ("admin", "leader")
    employee_id = user.get("employee_id")
    
    st.markdown("""
    <style>
    .msg-card {
        background: #1A1D27;
        border: 1px solid #2E3350;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    .msg-card:hover {
        border-color: #4F6BFF;
    }
    .msg-card.unread {
        border-left: 4px solid #4F6BFF;
    }
    .msg-sender {
        font-weight: 600;
        color: #E8EAF0;
        font-size: 0.95rem;
    }
    .msg-subject {
        color: #C8CADE;
        font-size: 0.9rem;
    }
    .msg-preview {
        color: #8B90A8;
        font-size: 0.82rem;
        margin-top: 2px;
    }
    .msg-time {
        color: #8B90A8;
        font-size: 0.7rem;
    }
    .msg-badge {
        background: #4F6BFF;
        color: white;
        border-radius: 50%;
        padding: 2px 8px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-left: 6px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ── Get unread count ────────────────────────────────────────────────────
    unread = get_unread_count(employee_id)
    
    # ── Tab selector ────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        f"📥 Inbox {'🔵' + str(unread) if unread > 0 else ''}", 
        "📤 Sent", 
        "✏️ Compose"
    ])
    
    # ── INBOX ──────────────────────────────────────────────────────────────
    with tab1:
        messages = get_messages_for_user(employee_id)
        received = [m for m in messages if m["receiver_id"] == employee_id]
        
        if not received:
            st.info("📭 No messages in your inbox.")
        else:
            for msg in received:
                is_unread = msg["is_read"] == 0
                card_class = "msg-card unread" if is_unread else "msg-card"
                
                with st.container():
                    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f'<div class="msg-sender">👤 {msg["sender_name"]} <span class="msg-badge" style="font-size:0.6rem;background:#2E3350;color:#8B90A8;">{msg["sender_role"]}</span></div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="msg-subject">📌 {msg["subject"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="msg-preview">{msg["message"][:100]}{"..." if len(msg["message"]) > 100 else ""}</div>', unsafe_allow_html=True)
                    with col2:
                        st.markdown(f'<div class="msg-time">{msg["created_at"][:16]}</div>', unsafe_allow_html=True)
                        if is_unread:
                            st.markdown('<span style="background:#4F6BFF;color:white;font-size:0.6rem;padding:2px 8px;border-radius:10px;">New</span>', unsafe_allow_html=True)
                    
                    # Expand to view full message
                    with st.expander("📖 Read Message", expanded=False):
                        st.markdown(f"**From:** {msg['sender_name']} ({msg['sender_role']})")
                        st.markdown(f"**Subject:** {msg['subject']}")
                        st.markdown(f"**Sent:** {msg['created_at']}")
                        st.markdown("---")
                        st.markdown(msg["message"])
                        
                        col_actions1, col_actions2, col_actions3 = st.columns([1, 1, 2])
                        with col_actions1:
                            if is_unread:
                                if st.button("✅ Mark as Read", key=f"read_{msg['id']}"):
                                    mark_message_as_read(msg["id"])
                                    st.rerun()
                        with col_actions2:
                            if st.button("🗑️ Delete", key=f"del_{msg['id']}"):
                                delete_message(msg["id"])
                                st.rerun()
                        with col_actions3:
                            # Reply button
                            if st.button("💬 Reply", key=f"reply_{msg['id']}"):
                                st.session_state.reply_to = msg
                                st.session_state.reply_mode = True
                                st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # ── SENT ────────────────────────────────────────────────────────────────
    with tab2:
        messages = get_messages_for_user(employee_id)
        sent = [m for m in messages if m["sender_id"] == employee_id]
        
        if not sent:
            st.info("📤 No sent messages.")
        else:
            for msg in sent:
                with st.container():
                    st.markdown(f'<div class="msg-card">', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f'<div class="msg-sender">📤 To: {msg["receiver_name"]} <span class="msg-badge" style="font-size:0.6rem;background:#2E3350;color:#8B90A8;">{msg["sender_role"]}</span></div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="msg-subject">📌 {msg["subject"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="msg-preview">{msg["message"][:100]}{"..." if len(msg["message"]) > 100 else ""}</div>', unsafe_allow_html=True)
                    with col2:
                        st.markdown(f'<div class="msg-time">{msg["created_at"][:16]}</div>', unsafe_allow_html=True)
                        status = "✅ Read" if msg["is_read"] == 1 else "⏳ Unread"
                        st.markdown(f'<span style="color:#8B90A8;font-size:0.6rem;">{status}</span>', unsafe_allow_html=True)
                    
                    with st.expander("📖 View Message", expanded=False):
                        st.markdown(f"**To:** {msg['receiver_name']}")
                        st.markdown(f"**Subject:** {msg['subject']}")
                        st.markdown(f"**Sent:** {msg['created_at']}")
                        st.markdown("---")
                        st.markdown(msg["message"])
                        
                        if st.button("🗑️ Delete", key=f"del_sent_{msg['id']}"):
                            delete_message(msg["id"])
                            st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # ── COMPOSE ─────────────────────────────────────────────────────────────
    with tab3:
        # Check if we're in reply mode
        reply_to = st.session_state.get("reply_to", None)
        reply_mode = st.session_state.get("reply_mode", False)
        
        if reply_mode and reply_to:
            st.info(f"💬 Replying to: **{reply_to['sender_name']}**")
            st.caption(f"Original subject: {reply_to['subject']}")
        
        st.markdown("### ✏️ Compose New Message")
        
        # Get all users except current user
        all_users = get_all_users()
        recipients = [
            u for u in all_users 
            if u["employee_id"] != employee_id
        ]
        
        # Filter recipients based on role
        recipient_options = {}
        for u in recipients:
            display_name = f"{u.get('full_name', '')} ({u.get('employee_id', '')})"
            if is_admin:
                # Admin/Leader can message anyone
                recipient_options[display_name] = u
            else:
                # Employees can only message admins and leaders
                if u["role"] in ("admin", "leader"):
                    recipient_options[display_name] = u
        
        if not recipient_options:
            st.warning("No recipients available to message.")
        else:
            # Default to reply recipient if in reply mode
            default_recipient = None
            if reply_mode and reply_to:
                for key, val in recipient_options.items():
                    if val["employee_id"] == reply_to["sender_id"]:
                        default_recipient = key
                        break
            
            recipient_label = st.selectbox(
                "Select Recipient",
                list(recipient_options.keys()),
                index=list(recipient_options.keys()).index(default_recipient) if default_recipient else 0
            )
            
            recipient = recipient_options[recipient_label]
            
            # Subject
            default_subject = ""
            if reply_mode and reply_to:
                default_subject = f"RE: {reply_to['subject']}"
            
            subject = st.text_input("Subject", value=default_subject)
            
            # Message body
            default_message = ""
            if reply_mode and reply_to:
                default_message = f"\n\n---\nOriginal message from {reply_to['sender_name']} ({reply_to['created_at'][:16]}):\n{reply_to['message']}"
            
            message = st.text_area("Message", height=200, value=default_message)
            
            # Send button
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("📤 Send Message", use_container_width=True, type="primary"):
                    if not subject or not message:
                        st.error("Please fill in both subject and message.")
                    else:
                        parent_id = reply_to["id"] if reply_mode and reply_to else None
                        
                        send_message(
                            sender_id=employee_id,
                            sender_name=user.get("full_name", "Unknown"),
                            sender_role=user["role"],
                            receiver_id=recipient["employee_id"],
                            receiver_name=recipient.get("full_name", "Unknown"),
                            subject=subject,
                            message=message,
                            parent_id=parent_id
                        )
                        
                        # Clear reply mode
                        st.session_state.reply_mode = False
                        st.session_state.reply_to = None
                        
                        st.success(f"✅ Message sent to {recipient.get('full_name', '')}!")
                        st.rerun()
        
        # Clear reply mode button
        if reply_mode:
            if st.button("❌ Cancel Reply"):
                st.session_state.reply_mode = False
                st.session_state.reply_to = None
                st.rerun()
