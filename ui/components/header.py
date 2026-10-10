"""
RailTrack Top Application Header.
Provides brand identity, connectivity status, and user session indicators.
"""

from typing import Optional, Dict, Any
import html
import streamlit as st
import requests
import os


def resolve_backend_url() -> str:
    """Resolve backend URL with intelligent Render deployment detection."""
    url = os.environ.get("BACKEND_URL", "").strip()
    if not url:
        if os.environ.get("RENDER") or os.environ.get("PORT"):
            return "https://sih26028-railway-backend.onrender.com"
        return "http://127.0.0.1:8000"
    if (url.rstrip("/").endswith("127.0.0.1:8000") or url.rstrip("/").endswith("localhost:8000")) and (os.environ.get("RENDER") or os.environ.get("PORT")):
        return "https://sih26028-railway-backend.onrender.com"
    return url.rstrip("/")


BACKEND_URL = resolve_backend_url()


@st.cache_data(ttl=15)
def get_backend_status() -> Dict[str, Any]:
    """Check backend operational status (cached for 15s)."""
    try:
        r = requests.get(f"{BACKEND_URL}/", timeout=1.5)
        if r.status_code == 200:
            return {"online": True, "status": "ONLINE"}
    except Exception:
        pass
    return {"online": False, "status": "OFFLINE_CACHE"}


def render_app_header() -> None:
    """Render the top persistent application header."""
    is_auth = st.session_state.get("authenticated", False)
    user = st.session_state.get("auth_user") or {}
    backend_info = get_backend_status()

    st_col_brand, st_col_status, st_col_user = st.columns([6, 3, 3])

    with st_col_brand:
        st.markdown(
            """
            <div class="rt-brand-title">
                <span style="font-size: 1.6rem;">🚆</span>
                <span>RailTrack</span>
                <span class="rt-badge rt-badge-reference" style="font-size:0.65rem; margin-left:6px;">PROD v2.1</span>
            </div>
            <div class="rt-brand-subtitle">
                Intelligent Passenger Services & Autonomous Section Operations
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st_col_status:
        if backend_info["online"]:
            badge_html = '<span class="rt-badge rt-badge-live">🟢 ENGINE CONNECTED</span>'
        else:
            badge_html = '<span class="rt-badge rt-badge-demo">🟡 OFFLINE / RESILIENT CACHE</span>'
        st.markdown(
            f'<div style="text-align: right; padding-top: 6px;">{badge_html}</div>',
            unsafe_allow_html=True,
        )

    with st_col_user:
        if is_auth:
            display_name = html.escape((user.get("name") or "User").split()[0])
            st.markdown(
                f'<div style="text-align: right; font-size: 0.85rem; font-weight: 600; color: #F1F5F9; padding-top: 6px;">'
                f'👤 {display_name} <span class="rt-badge rt-badge-historical" style="font-size:0.65rem;">Active</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="text-align: right; font-size: 0.85rem; color: #A9BAD3; padding-top: 6px;">'
                '👤 Guest Passenger'
                '</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height: 1px; background: #2A3B57; margin: 0.6rem 0 1.2rem 0;"></div>', unsafe_allow_html=True)
