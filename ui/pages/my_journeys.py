"""
RailTrack Page 8 — My Journey / Saved Trips.
Personalized passenger trip dashboard featuring saved PNR tickets, active itineraries,
recently viewed train routes, and direct links to live tracking and coach positioning.
Provides cloud sign-in prompts and honest empty states.
"""

from typing import Dict, Any
import html
import streamlit as st

from ui.components.header import render_app_header
from ui.components.provenance import get_provenance_badge_html


def render_my_journeys_page() -> None:
    """Render the personalized passenger journey and saved trips dashboard."""
    render_app_header()

    from passenger_app import (
        render_verified_ticket_card,
        render_coach_formation_html,
        clear_journey_from_backend,
    )

    ticket = st.session_state.get("verified_ticket")
    is_auth = st.session_state.get("authenticated", False)
    user = st.session_state.get("auth_user") or {}

    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #071530 0%, #1E40AF 100%); border-radius: 14px; padding: 1.5rem 1.25rem; color: #FFFFFF; margin-bottom: 1.25rem; box-shadow: 0 4px 16px rgba(7, 21, 48, 0.15);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                <div>
                    <div style="font-size: 1.5rem; font-weight: 800; margin-bottom: 0.35rem; letter-spacing: -0.02em;">
                        🧳 My Journey & Saved Trips
                    </div>
                    <div style="font-size: 0.85rem; color: #BFDBFE; font-weight: 500;">
                        {f"Synced Account: <b>{html.escape(user.get('name', 'Passenger'))}</b>" if is_auth else "Local Device Session · Sign in to sync across devices"}
                    </div>
                </div>
                <div>
                    {get_provenance_badge_html("VERIFIED LIVE" if ticket else "REFERENCE DATA")}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not ticket:
        # Honest Empty State
        st.markdown('<div class="rt-card" style="margin-bottom: 1.25rem;">', unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: center; padding: 2rem 1rem;">
                <div style="font-size: 2.8rem; margin-bottom: 0.5rem;">🎫</div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin-bottom: 0.35rem;">No Active Journey Saved</div>
                <div style="font-size: 0.85rem; color: #64748B; max-width: 480px; margin: 0 auto 1.5rem auto;">
                    You do not have any saved railway trips in this session. Enter your 10-digit IRCTC PNR or scan an e-ticket to unlock real-time station alerts, coach positioning, and destination wake-up alarms.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_pnr, col_live, col_coach = st.columns(3)
        with col_pnr:
            if st.button("🎫 Check & Link PNR", type="primary", use_container_width=True, key="my_j_link_pnr"):
                from ui.routing import page_pnr
                st.switch_page(page_pnr)
        with col_live:
            if st.button("📍 Live Train Status", use_container_width=True, key="my_j_nav_live"):
                from ui.routing import page_live_status
                st.switch_page(page_live_status)
        with col_coach:
            if st.button("💺 Find My Coach", use_container_width=True, key="my_j_nav_coach"):
                from ui.routing import page_coach_position
                st.switch_page(page_coach_position)

        st.markdown('</div>', unsafe_allow_html=True)

        # Sign-in prompt for persistent account storage
        if not is_auth:
            st.markdown(
                """
                <div class="rt-card" style="background: #F8FAFC; border: 1px dashed #CBD5E1; margin-bottom: 1.25rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <div style="font-weight: 700; color: #0F172A; font-size: 0.95rem;">🔒 Cloud Storage & Journey History</div>
                            <div style="font-size: 0.8rem; color: #64748B;">
                                Sign in to your RailTrack account to securely sync saved PNRs across all your mobile and desktop devices.
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            col_auth_cta, _ = st.columns([3, 4])
            with col_auth_cta:
                if st.button("🔑 Sign In / Register Account", use_container_width=True, key="my_j_sign_in_cta"):
                    from ui.routing import page_auth
                    st.switch_page(page_auth)

        # Recently viewed routes
        st.markdown(
            """
            <div class="rt-card">
                <div class="rt-card-title">🕒 Recently Searched Routes</div>
                <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 8px;">Quick-access frequent corridors:</div>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <div style="padding: 0.6rem 0.85rem; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600; color: #0F172A; font-size: 0.85rem;">New Delhi (NDLS) → Kanpur Central (CNB)</span>
                        <span style="font-size: 0.75rem; color: #1E40AF; font-weight: 600;">12004 Shatabdi / 22436 Vande Bharat</span>
                    </div>
                    <div style="padding: 0.6rem 0.85rem; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600; color: #0F172A; font-size: 0.85rem;">New Delhi (NDLS) → Jammu Tawi (JAT)</span>
                        <span style="font-size: 0.75rem; color: #1E40AF; font-weight: 600;">22439 Vande Bharat / 12425 Rajdhani</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # If active ticket exists:
    render_verified_ticket_card(ticket)

    jrny = ticket.get("journey", {})
    bkg = ticket.get("booking", {})
    tr_num = jrny.get("train_number", "22436")
    coach_id = bkg.get("coach", "C4")
    seat_num = str(bkg.get("seat_number", "28"))

    # Quick Actions Row
    st.markdown('<div class="rt-card" style="margin-top: 1rem;">', unsafe_allow_html=True)
    st.markdown('<div class="rt-card-title">⚡ Journey Actions</div>', unsafe_allow_html=True)

    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button(f"📍 Track Live {tr_num}", type="primary", use_container_width=True, key="my_j_btn_track"):
            st.session_state["train_search_query"] = tr_num
            from ui.routing import page_live_status
            st.switch_page(page_live_status)
    with b2:
        if st.button(f"💺 Coach {coach_id} Locator", use_container_width=True, key="my_j_btn_coach"):
            st.session_state["coach_train_select"] = tr_num
            st.session_state["coach_id_input"] = coach_id
            st.session_state["seat_num_input"] = seat_num
            from ui.routing import page_coach_position
            st.switch_page(page_coach_position)
    with b3:
        if st.button("🔔 Arm Wake-Up Alarm", use_container_width=True, key="my_j_btn_alarm"):
            st.session_state["dest_alarm_enabled"] = True
            st.session_state["dest_alarm_dismissed"] = False
            st.toast("⏰ Destination wake-up alarm armed!")
    with b4:
        if st.button("🗑️ Unlink Journey", use_container_width=True, key="my_j_btn_unlink"):
            clear_journey_from_backend()
            st.session_state["verified_ticket"] = None
            st.toast("Journey unlinked.")
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Coach formation snapshot
    formation_html = render_coach_formation_html(tr_num, coach_id, seat_num)
    from passenger_app import clean_html
    st.markdown(clean_html(formation_html), unsafe_allow_html=True)


if __name__ == "__main__":
    from ui.theme import inject_custom_theme
    inject_custom_theme()
    render_my_journeys_page()
