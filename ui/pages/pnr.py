"""
PNR & Booking Status Page.
ConfirmTkt style clean PNR search, barcode/QR ticket scanning, and verified Electronic Reservation Slip (ERS).
"""

import html
import streamlit as st

from ui.components.header import render_app_header
from ui.components.provenance import get_provenance_badge_html


def render_pnr_page() -> None:
    """Render dedicated PNR enquiry and ticket verification page."""
    render_app_header()

    from passenger_app import (
        fetch_ticket,
        decode_qr_image,
        render_verified_ticket_card,
        save_journey_to_backend,
    )

    if "verified_ticket" not in st.session_state:
        st.session_state.verified_ticket = None

    st.markdown(
        """
        <div style="background: #101D37; border: 1px solid #2A3B57; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div>
                    <span class="rt-card-title">🎫 PNR Status & Boarding Pass Verification</span>
                    <div style="font-size:0.8rem; color:#A9BAD3; margin-top:2px;">
                        Enter your 10-digit Indian Railways PNR to check current booking status, coach allotment, and berth type.
                    </div>
                </div>
                <span class="rt-badge rt-badge-live">IRCTC MANIFEST VERIFIED</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_manual, tab_scan, tab_demo = st.tabs(["✍️ Enter 10-Digit PNR", "📷 Scan Ticket QR / Photo", "🧪 Verified Sample Tickets"])

    with tab_manual:
        c_inp, c_btn, c_clr = st.columns([5, 2, 1.5])
        with c_inp:
            pnr_val = st.text_input(
                "PNR Number",
                placeholder="Enter 10-digit PNR (e.g., 8429103847, 2840192841, 1948201948)",
                label_visibility="collapsed",
                key="pnr_page_input",
            )
        with c_btn:
            check_pnr = st.button("Check Status 🔍", type="primary", use_container_width=True, key="pnr_page_check_btn")
        with c_clr:
            if st.button("Reset", use_container_width=True, key="pnr_page_reset_btn"):
                st.session_state.verified_ticket = None
                st.rerun()

        if check_pnr:
            clean_pnr = pnr_val.strip()
            if not clean_pnr or len(clean_pnr) != 10 or not clean_pnr.isdigit():
                st.error("Please enter a valid 10-digit numeric Indian Railways PNR number.")
            else:
                with st.spinner("Verifying PNR against passenger manifest..."):
                    res = fetch_ticket(clean_pnr)
                    if res.get("match_verified"):
                        st.session_state.verified_ticket = res
                        if st.session_state.get("authenticated"):
                            save_journey_to_backend(res)
                        st.toast("✅ PNR verified successfully!")
                        st.rerun()
                    else:
                        st.error(res.get("message") or "PNR record not found. Please check number.")

    with tab_scan:
        st.write("Upload an image of your printed IRCTC e-ticket or point your device camera at the ticket QR code:")
        cam_pic = st.camera_input("Scan QR Code", key="pnr_page_cam")
        if cam_pic:
            with st.spinner("Analyzing QR code..."):
                img_bytes = cam_pic.getvalue()
                decoded = decode_qr_image(img_bytes)
                if decoded:
                    res = fetch_ticket(decoded)
                    if res.get("match_verified"):
                        st.session_state.verified_ticket = res
                        st.toast("✅ Ticket QR decoded successfully!")
                        st.rerun()
                    else:
                        st.error("Unrecognized ticket QR code payload.")
                else:
                    st.warning("Could not detect a clear QR code. Please position the code in good lighting or enter PNR manually.")

    with tab_demo:
        st.write("Click any verified reference ticket to test instant PNR resolution:")
        d1, d2, d3 = st.columns(3)
        with d1:
            if st.button("🎫 8429103847 (Vande Bharat C6/46)", use_container_width=True, key="pnr_demo_1"):
                st.session_state.verified_ticket = fetch_ticket("8429103847")
                st.rerun()
        with d2:
            if st.button("🎫 2840192841 (Rajdhani B1/32)", use_container_width=True, key="pnr_demo_2"):
                st.session_state.verified_ticket = fetch_ticket("2840192841")
                st.rerun()
        with d3:
            if st.button("🎫 1948201948 (Shatabdi C4/12)", use_container_width=True, key="pnr_demo_3"):
                st.session_state.verified_ticket = fetch_ticket("1948201948")
                st.rerun()

    # Display Verified Ticket Card if exists
    ticket = st.session_state.get("verified_ticket")
    if ticket:
        render_verified_ticket_card(ticket)

        bkg = ticket.get("booking", {})
        jrny = ticket.get("journey", {})

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button(f"💺 Locate Coach {bkg.get('coach', '')} on Train {jrny.get('train_number', '')}", type="primary", use_container_width=True, key="pnr_locate_coach_btn"):
                st.session_state["coach_train_select"] = jrny.get("train_number")
                st.session_state["coach_id_input"] = bkg.get("coach")
                st.session_state["seat_num_input"] = bkg.get("seat_number")
                from ui.routing import page_coach_position
                st.switch_page(page_coach_position)

        with action_col2:
            if st.button("🧳 View in My Journeys", use_container_width=True, key="pnr_go_to_my_journeys"):
                from ui.routing import page_my_journeys
                st.switch_page(page_my_journeys)


if __name__ == "__main__":
    from ui.theme import inject_custom_theme
    inject_custom_theme()
    render_pnr_page()
