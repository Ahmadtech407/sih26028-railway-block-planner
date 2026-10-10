"""
Account & Settings Page.
Handles user profile, JWT authentication (login/signup), session management, and passenger preferences.
"""

import html
import streamlit as st

from ui.components.header import render_app_header
from ui.components.provenance import get_provenance_badge_html


def render_account_page() -> None:
    """Render account management and settings page."""
    render_app_header()

    from passenger_app import (
        auth_request,
        sign_out,
    )

    is_auth = st.session_state.get("authenticated", False)
    user = st.session_state.get("auth_user") or {}

    if not is_auth:
        st.markdown('<div class="rt-card">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="rt-card-header">
                <span class="rt-card-title">🔐 RailTrack Account Authentication</span>
                <span class="rt-badge rt-badge-reference">SECURE JWT AUTH</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_signup = st.tabs(["🔑 Sign In", "📝 Create New Account"])

        with tab_login:
            with st.form("account_page_login_form"):
                login_id = st.text_input("Mobile Number or Email", placeholder="e.g. passenger@railtrack.in or 9876543210")
                login_pwd = st.text_input("Password", type="password", placeholder="Enter your password")
                login_submit = st.form_submit_button("Sign In 🚀", type="primary", use_container_width=True)

            if login_submit:
                if not login_id.strip() or not login_pwd:
                    st.error("Please enter both your identifier and password.")
                else:
                    with st.spinner("Authenticating credentials..."):
                        ok, data, err = auth_request("/api/auth/login", {"identifier": login_id.strip(), "password": login_pwd})
                        if ok:
                            st.session_state["authenticated"] = True
                            st.session_state["auth_token"] = data.get("access_token")
                            st.session_state["auth_user"] = data.get("user")
                            st.toast("Signed in successfully!")
                            st.rerun()
                        else:
                            st.error(err or "Invalid credentials. Please verify.")

        with tab_signup:
            with st.form("account_page_signup_form"):
                su_name = st.text_input("Full Name", placeholder="e.g. Ramesh Kumar")
                su_id = st.text_input("Mobile Number or Email", placeholder="e.g. ramesh@railtrack.in or 9876543210")
                su_pwd = st.text_input("Password (min 8 chars)", type="password", placeholder="Create password")
                su_pwd_conf = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                su_submit = st.form_submit_button("Create Account ✨", type="primary", use_container_width=True)

            if su_submit:
                if not su_name.strip() or not su_id.strip() or not su_pwd:
                    st.error("All fields are required.")
                elif len(su_pwd) < 8:
                    st.error("Password must be at least 8 characters.")
                elif su_pwd != su_pwd_conf:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Creating RailTrack account..."):
                        ok, data, err = auth_request(
                            "/api/auth/signup",
                            {"name": su_name.strip(), "identifier": su_id.strip(), "password": su_pwd},
                        )
                        if ok:
                            st.session_state["authenticated"] = True
                            st.session_state["auth_token"] = data.get("access_token")
                            st.session_state["auth_user"] = data.get("user")
                            st.toast("Account created successfully!")
                            st.rerun()
                        else:
                            st.error(err or "Registration error.")

        st.markdown('</div>', unsafe_allow_html=True)
        return

    # If already authenticated:
    st.markdown('<div class="rt-card">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="rt-card-header">
            <div>
                <span class="rt-card-title">👤 Passenger Profile</span>
                <div style="font-size:0.8rem; color:#64748B;">Authenticated RailTrack Account</div>
            </div>
            <div>
                {get_provenance_badge_html("VERIFIED LIVE", source="JWT_SESSION_ACTIVE")}
            </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 12px 0;">
            <div class="rt-metric-pill">
                <span class="rt-metric-label">Full Name</span>
                <span class="rt-metric-val" style="font-size:1.0rem;">{html.escape(user.get('name', 'User'))}</span>
            </div>
            <div class="rt-metric-pill">
                <span class="rt-metric-label">Role</span>
                <span class="rt-metric-val" style="font-size:1.0rem; color:#1E40AF;">{html.escape(user.get('role', 'PASSENGER'))}</span>
            </div>
            <div class="rt-metric-pill">
                <span class="rt-metric-label">Account ID</span>
                <span class="rt-metric-val" style="font-size:0.9rem;">{html.escape(str(user.get('id', 'USR-01')))}</span>
            </div>
            <div class="rt-metric-pill">
                <span class="rt-metric-label">Session Status</span>
                <span class="rt-metric-val" style="font-size:0.9rem; color:#059669;">AUTHENTICATED</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Preferences & Controls
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="rt-card-title" style="font-size:0.95rem;">⚙️ Passenger Preferences</div>', unsafe_allow_html=True)

    pref_col1, pref_col2 = st.columns(2)
    with pref_col1:
        st.checkbox("Audible IRCTC Station Chime on Arrival", value=True, key="pref_chime")
        st.checkbox("High-Contrast Accessible Mode", value=False, key="pref_contrast")
    with pref_col2:
        st.checkbox("Auto-Sync Saved Itineraries to Cloud", value=True, key="pref_sync")
        st.checkbox("Receive Platform Change Advisories", value=True, key="pref_plat_alert")

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    col_signout, _ = st.columns([2, 5])
    with col_signout:
        if st.button("🚪 Sign Out of RailTrack", type="primary", use_container_width=True, key="btn_account_signout"):
            sign_out()
            st.toast("Signed out successfully.")
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    from ui.theme import inject_custom_theme
    inject_custom_theme()
    render_account_page()
