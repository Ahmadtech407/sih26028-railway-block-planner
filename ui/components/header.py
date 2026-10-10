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
            if st.button(f"👤 {display_name}", key="hdr_user_profile_btn", help="Account & Settings", use_container_width=True):
                from ui.routing import page_auth
                st.switch_page(page_auth)
        else:
            if st.button("🔐 Sign In", key="hdr_signin_btn", help="Sign In / Register", use_container_width=True):
                from ui.routing import page_auth
                st.switch_page(page_auth)

    st.markdown('<div style="height: 1px; background: #2A3B57; margin: 0.5rem 0 0.65rem 0;"></div>', unsafe_allow_html=True)

    # Persistent Service Navigation Strip (Ensures immediate 1-click access across all views)
    n1, n2, n3, n4, n5, n6, n7, n8 = st.columns(8)
    with n1:
        if st.button("🏠 Home", key="hdr_nav_home", use_container_width=True):
            from ui.routing import page_home
            st.switch_page(page_home)
    with n2:
        if st.button("🤖 Best Train", key="hdr_nav_best", use_container_width=True):
            from ui.routing import page_find_best_train
            st.switch_page(page_find_best_train)
    with n3:
        if st.button("📍 Live Track", key="hdr_nav_live", use_container_width=True):
            from ui.routing import page_live_status
            st.switch_page(page_live_status)
    with n4:
        if st.button("💺 Coach", key="hdr_nav_coach", use_container_width=True):
            from ui.routing import page_coach_position
            st.switch_page(page_coach_position)
    with n5:
        if st.button("🎫 PNR", key="hdr_nav_pnr", use_container_width=True):
            from ui.routing import page_pnr
            st.switch_page(page_pnr)
    with n6:
        if st.button("🔍 Trains", key="hdr_nav_trains", use_container_width=True):
            from ui.routing import page_trains
            st.switch_page(page_trains)
    with n7:
        if st.button("🧳 Trips", key="hdr_nav_journey", use_container_width=True):
            from ui.routing import page_my_journey
            st.switch_page(page_my_journey)
    with n8:
        if st.button("🔔 Alerts", key="hdr_nav_alerts", use_container_width=True):
            from ui.routing import page_alerts
            st.switch_page(page_alerts)

    st.markdown('<div style="height: 1px; background: rgba(42, 59, 87, 0.6); margin: 0.45rem 0 1rem 0;"></div>', unsafe_allow_html=True)

