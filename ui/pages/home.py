"""
RailTrack Page 1 — Home.
Clean, compact, and action-oriented passenger dashboard.
Provides station search with swap controls, quick-action service shortcuts,
compact AI journey assistant launcher, recent searches, and travel notices.
Excludes heavy maps, detailed timelines, and coach diagrams to prevent long scrolling.
"""

from datetime import datetime, date
import html
import streamlit as st

from ui.components.header import render_app_header
from ui.components.provenance import get_provenance_badge_html


STATION_OPTIONS = [
    "New Delhi (NDLS)",
    "Kanpur Central (CNB)",
    "Prayagraj Junction (PRYJ)",
    "Jammu Tawi (JAT)",
    "Ludhiana Junction (LDH)",
    "Varanasi Junction (BSB)",
    "Howrah Junction (HWH)",
    "Lucknow Charbagh (LKO)",
]


def render_home_page() -> None:
    """Render the clean, compact RailTrack passenger travel homepage."""
    render_app_header()

    # 1. Hero Welcome Header
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #071530 0%, #1E40AF 100%); border-radius: 14px; padding: 1.5rem 1.25rem; color: #FFFFFF; margin-bottom: 1.25rem; box-shadow: 0 4px 16px rgba(7, 21, 48, 0.15);">
            <div style="font-size: 1.5rem; font-weight: 800; margin-bottom: 0.35rem; letter-spacing: -0.02em;">
                Where is your next journey?
            </div>
            <div style="font-size: 0.85rem; color: #BFDBFE; font-weight: 500;">
                Live train radar, coach positioning, PNR verification & AI travel intelligence.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Search Trains & Timetables
    with st.container():
        st.markdown('<div class="rt-card-title" style="margin-bottom: 0.75rem;">🔍 Search Trains & Timetables</div>', unsafe_allow_html=True)

        scol1, scol_swap, scol2, scol3 = st.columns([4, 1, 4, 3])

        default_from = st.session_state.get("passenger_from", "New Delhi (NDLS)")
        default_to = st.session_state.get("passenger_to", "Kanpur Central (CNB)")

        with scol1:
            from_stn = st.selectbox(
                "From Station",
                STATION_OPTIONS,
                index=STATION_OPTIONS.index(default_from) if default_from in STATION_OPTIONS else 0,
                key="home_from_select",
            )
        with scol_swap:
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
            if st.button("⇄", key="home_swap_btn", help="Swap Source and Destination", use_container_width=True):
                st.session_state["passenger_from"] = default_to
                st.session_state["passenger_to"] = default_from
                st.rerun()
        with scol2:
            to_stn = st.selectbox(
                "To Station",
                STATION_OPTIONS,
                index=STATION_OPTIONS.index(default_to) if default_to in STATION_OPTIONS else 1,
                key="home_to_select",
            )
        with scol3:
            journey_date = st.date_input(
                "Journey Date",
                value=date.today(),
                key="home_date_input",
            )

        if st.button("🚆 Search Available Trains", key="home_search_submit_btn", type="primary", use_container_width=True):
            st.session_state["passenger_from"] = from_stn
            st.session_state["passenger_to"] = to_stn
            from ui.routing import page_trains
            st.switch_page(page_trains)

    # 3. 4 Essential Service Shortcuts (Quick Actions)
    st.markdown('<div style="font-size:1.05rem; font-weight:700; color:#F1F5F9; margin: 1.25rem 0 0.75rem 0;">⚡ Essential Passenger Services</div>', unsafe_allow_html=True)

    qcol1, qcol2, qcol3, qcol4 = st.columns(4)

    with qcol1:
        st.markdown(
            """
            <div class="rt-service-tile">
                <div class="rt-service-icon">📍</div>
                <div class="rt-service-name">Live Train Status</div>
                <div class="rt-service-desc">Track real-time delays & station progression</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Track Live Status", key="btn_quick_live", use_container_width=True):
            from ui.routing import page_live_status
            st.switch_page(page_live_status)

    with qcol2:
        st.markdown(
            """
            <div class="rt-service-tile">
                <div class="rt-service-icon">🎫</div>
                <div class="rt-service-name">PNR Status</div>
                <div class="rt-service-desc">Verify confirmation status & e-ticket slip</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Check PNR Status", key="btn_quick_pnr", use_container_width=True):
            from ui.routing import page_pnr
            st.switch_page(page_pnr)

    with qcol3:
        st.markdown(
            """
            <div class="rt-service-tile">
                <div class="rt-service-icon">💺</div>
                <div class="rt-service-name">Find My Coach</div>
                <div class="rt-service-desc">Authentic rake order, loco distance & seat layout</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Locate My Coach", key="btn_quick_coach", use_container_width=True):
            from ui.routing import page_coach_position
            st.switch_page(page_coach_position)

    with qcol4:
        st.markdown(
            """
            <div class="rt-service-tile">
                <div class="rt-service-icon">🤖</div>
                <div class="rt-service-name">Find Best Train</div>
                <div class="rt-service-desc">AI assistant with deadline & ML delay ranking</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("AI Assistant", key="btn_quick_ai_train", use_container_width=True):
            from ui.routing import page_find_best_train
            st.switch_page(page_find_best_train)

    # 4. Compact Journey Assistant Entry Point
    st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown(
            """
            <div style="background: #101D37; border: 1px solid #2A3B57; border-left: 4px solid #38BDF8; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.75rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <div>
                        <div style="font-weight: 700; color: #F1F5F9; font-size: 0.95rem;">🤖 AI Journey Assistant — Need a Smart Recommendation?</div>
                        <div style="font-size: 0.78rem; color: #A9BAD3;">Ask in plain English with your arrival deadline or travel preferences.</div>
                    </div>
                    <span class="rt-badge rt-badge-predicted">ML + TIMETABLES</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form(key="home_compact_assistant_form"):
            ac1, ac2 = st.columns([5, 2])
            with ac1:
                home_ai_input = st.text_input(
                    "Natural Language Travel Request",
                    placeholder="e.g. I need to reach Jammu from Delhi before 8 PM",
                    label_visibility="collapsed",
                    key="home_compact_ai_input",
                )
            with ac2:
                home_ai_submit = st.form_submit_button("Ask Journey Assistant 🚀", type="primary", use_container_width=True)

        if home_ai_submit and home_ai_input.strip():
            st.session_state["journey_assistant_query"] = home_ai_input.strip()
            # Perform search and navigate to Page 2
            from passenger_app import query_journey_assistant_api
            with st.spinner("Analyzing verified schedules and ML delay models..."):
                res = query_journey_assistant_api(home_ai_input.strip())
                st.session_state["journey_assistant_result"] = res
            from ui.routing import page_find_best_train
            st.switch_page(page_find_best_train)

    # 5. Active Journey Card or Recent Searches
    verified_ticket = st.session_state.get("verified_ticket")
    if verified_ticket:
        bkg = verified_ticket.get("booking", {})
        jrny = verified_ticket.get("journey", {})
        psg = verified_ticket.get("passenger", {})
        st.markdown(
            f"""
            <div class="rt-card" style="border-left: 4px solid #10B981; margin-bottom: 1.25rem;">
                <div class="rt-card-header">
                    <div>
                        <span class="rt-card-title">🎫 Active Journey: {html.escape(jrny.get('train_name', 'Train'))} ({html.escape(jrny.get('train_number', ''))})</span>
                        <div style="font-size:0.75rem; color:#A9BAD3;">PNR: <b>{html.escape(str(verified_ticket.get('pnr', '')))}</b> · Passenger: {html.escape(psg.get('name', ''))}</div>
                    </div>
                    <div>
                        <span class="rt-badge rt-badge-live">✓ {html.escape(str(bkg.get('status', 'CNF')))}</span>
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div>
                        <div style="font-size:0.78rem; color:#A9BAD3;">Route</div>
                        <div style="font-weight:700; color:#F1F5F9;">{html.escape(jrny.get('from_station', ''))} → {html.escape(jrny.get('to_station', ''))}</div>
                    </div>
                    <div>
                        <div style="font-size:0.78rem; color:#A9BAD3;">Coach & Berth</div>
                        <div style="font-weight:700; color:#38BDF8;">Coach {html.escape(str(bkg.get('coach', '')))} · Berth {html.escape(str(bkg.get('seat_number', '')))} ({html.escape(str(bkg.get('berth_type', '')))})</div>
                    </div>
                    <div>
                        <div style="font-size:0.78rem; color:#A9BAD3;">Travel Date</div>
                        <div style="font-weight:700; color:#F1F5F9;">{html.escape(str(jrny.get('travel_date', 'Today')))}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Recently Viewed / Popular Routes
        st.markdown(
            """
            <div style="background: #101D37; border: 1px solid #2A3B57; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 1.25rem;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #A9BAD3; margin-bottom: 0.5rem;">🔥 Popular Passenger Routes:</div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <span style="background: #162640; border: 1px solid #2A3B57; color: #F1F5F9; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;">
                        New Delhi ⇄ Kanpur Central
                    </span>
                    <span style="background: #162640; border: 1px solid #2A3B57; color: #F1F5F9; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;">
                        New Delhi ⇄ Jammu Tawi
                    </span>
                    <span style="background: #162640; border: 1px solid #2A3B57; color: #F1F5F9; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;">
                        New Delhi ⇄ Howrah Junction
                    </span>
                    <span style="background: #162640; border: 1px solid #2A3B57; color: #F1F5F9; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;">
                        Kanpur Central ⇄ Prayagraj Jn
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 6. Relevant Travel Notice & Operational Advisory
    st.markdown(
        """
        <div style="padding: 0.85rem 1rem; background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 8px; font-size: 0.75rem; color: #FBBF24; line-height: 1.5; margin-bottom: 1.25rem;">
            ⚠️ <b>Operational Travel Advisory</b>: Sectional speed restrictions (TSR) are active between Kanpur and Prayagraj for automated track renewal. Live safety clearances and train dispatching are controlled under Indian Railways G&SR rules.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 7. Non-vital Platform Notice Footer
    st.markdown(
        """
        <div style="padding: 0.75rem 1rem; background: #0B1730; border: 1px solid #2A3B57; border-radius: 8px; font-size: 0.72rem; color: #A9BAD3; line-height: 1.5;">
            🏛️ <b>RailTrack Transparency & Safety Notice</b>: RailTrack provides passenger journey intelligence and multi-train section optimization. Station platforms, timetables, and delay predictions are matched against verified railway database records. Rail Madad helpline: <b>139</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    from ui.theme import inject_custom_theme
    inject_custom_theme()
    render_home_page()
