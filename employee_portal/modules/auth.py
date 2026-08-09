"""
modules/auth.py
Login page and session management.
"""

import streamlit as st
from modules.database import verify_login


def login_page():
    """Render the login screen."""

    st.markdown("""
    <style>
    .login-logo {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        background: linear-gradient(135deg, #4F6BFF, #7C3AED);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .login-sub {
        text-align: center;
        color: #8B90A8;
        font-size: 0.875rem;
        margin-bottom: 2rem;
    }
    .login-title {
        font-size: 1.35rem;
        font-weight: 600;
        color: #E8EAF0;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 1.5, 1])
    with col_c:
        st.markdown('<div class="login-logo"><img src="https://plain-eeur-prod-public.komododecks.com/202608/09/cTbwjWfVAMvKzMZ4n8ET/image.png" style="height:72px;vertical-align:middle;margin-right:10px"> Hunter Portal</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Employee Performance & Management System</div>',
                    unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="login-title">Sign In</div>', unsafe_allow_html=True)

            username = st.text_input("Username", placeholder="Enter your username",
                                     key="login_user")
            password = st.text_input("Password", type="password",
                                     placeholder="Enter your password", key="login_pw")

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                login_btn = st.button("Sign In →", use_container_width=True)

            if login_btn:
                if not username or not password:
                    st.error("Please fill in all fields.")
                else:
                    user = verify_login(username.strip(), password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")


def logout():
    """Clear session and rerun."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
