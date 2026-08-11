"""
modules/tabs/maps_tab.py
Google Maps tab — type an address and open it on the map inside the portal.
"""

import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import quote


def render_maps_tab(user: dict):
    st.markdown("""
    <style>
    .maps-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: #E8EAF0;
        margin-bottom: 0.5rem;
    }
    .maps-sub {
        color: #8B90A8;
        font-size: 0.85rem;
        margin-bottom: 1.25rem;
    }
    .map-wrap {
        background: #1A1D27;
        border: 1px solid #2E3350;
        border-radius: 16px;
        padding: 1.25rem;
    }
    div[data-testid="stTextInput"] input {
        font-size: 1rem !important;
        padding: 0.65rem 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="maps-header">🗺️ Google Maps</div>', unsafe_allow_html=True)
    st.markdown('<div class="maps-sub">Type an address and press Enter or click Search to open it on the map.</div>',
                unsafe_allow_html=True)

    # ── Search bar ────────────────────────────────────────────────────────────
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        address = st.text_input(
            label="Address",
            placeholder="e.g. Cairo Tower, Cairo, Egypt",
            key="maps_address",
            label_visibility="collapsed"
        )
    with col_btn:
        search_btn = st.button("🔍 Search", use_container_width=True, key="maps_search_btn")

    # ── Quick shortcuts ───────────────────────────────────────────────────────
    st.markdown('<div style="margin:0.5rem 0 1rem;color:#8B90A8;font-size:0.8rem">⚡ Quick select:</div>',
                unsafe_allow_html=True)
    shortcuts = [
        "Cairo, Egypt",
        "Alexandria, Egypt",
        "Giza, Egypt",
        "Maadi, Cairo",
        "Nasr City, Cairo",
    ]
    cols = st.columns(len(shortcuts))
    for i, place in enumerate(shortcuts):
        with cols[i]:
            if st.button(place, key=f"shortcut_{i}", use_container_width=True):
                st.session_state.maps_address = place
                st.session_state.maps_query   = place
                st.rerun()

    # ── Determine which address to show ──────────────────────────────────────
    query = None
    if search_btn and address.strip():
        query = address.strip()
        st.session_state.maps_query = query
    elif "maps_query" in st.session_state and st.session_state.maps_query:
        query = st.session_state.maps_query
    elif address.strip():
        query = address.strip()
        st.session_state.maps_query = query

    # ── Map iframe ────────────────────────────────────────────────────────────
    st.markdown('<div class="map-wrap">', unsafe_allow_html=True)

    if query:
        encoded = quote(query)
        embed_url = (
            f"https://maps.google.com/maps?q={encoded}"
            f"&output=embed&hl=en&z=15"
        )
        st.markdown(f"""
        <div style="margin-bottom:0.75rem;display:flex;align-items:center;gap:8px">
            <span style="color:#4F6BFF;font-size:1rem">📍</span>
            <span style="color:#E8EAF0;font-weight:600;font-size:0.95rem">{query}</span>
            <a href="https://maps.google.com/maps?q={encoded}" target="_blank"
               style="margin-left:auto;color:#4F6BFF;font-size:0.8rem;
                      text-decoration:none;border:1px solid #4F6BFF44;
                      padding:3px 10px;border-radius:8px">
                ↗️ Open in Google Maps
            </a>
        </div>
        """, unsafe_allow_html=True)

        components.iframe(embed_url, height=520, scrolling=False)

        # ── Action buttons ────────────────────────────────────────────────────
        col1, col2, col3 = st.columns(3)
        with col1:
            directions_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded}"
            st.markdown(f"""
            <a href="{directions_url}" target="_blank">
                <button style="width:100%;background:linear-gradient(135deg,#4F6BFF,#7C3AED);
                               color:white;border:none;border-radius:10px;padding:0.5rem;
                               font-size:0.85rem;font-weight:600;cursor:pointer">
                    🧭 Directions
                </button>
            </a>""", unsafe_allow_html=True)
        with col2:
            street_url = f"https://www.google.com/maps?q={encoded}&layer=c"
            st.markdown(f"""
            <a href="{street_url}" target="_blank">
                <button style="width:100%;background:#1A1D27;color:#E8EAF0;
                               border:1px solid #2E3350;border-radius:10px;padding:0.5rem;
                               font-size:0.85rem;font-weight:600;cursor:pointer">
                    🚶 Street View
                </button>
            </a>""", unsafe_allow_html=True)
        with col3:
            satellite_url = f"https://www.google.com/maps?q={encoded}&t=k"
            st.markdown(f"""
            <a href="{satellite_url}" target="_blank">
                <button style="width:100%;background:#1A1D27;color:#E8EAF0;
                               border:1px solid #2E3350;border-radius:10px;padding:0.5rem;
                               font-size:0.85rem;font-weight:600;cursor:pointer">
                    🛰️ Satellite View
                </button>
            </a>""", unsafe_allow_html=True)

    else:
        # Placeholder when no address entered yet
        st.markdown("""
        <div style="height:420px;display:flex;flex-direction:column;
                    align-items:center;justify-content:center;gap:12px">
            <div style="font-size:4rem">🗺️</div>
            <div style="color:#8B90A8;font-size:1rem;text-align:center">
                Type an address above and press Enter or click Search<br>
                <span style="font-size:0.8rem">to view the location on the map.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
