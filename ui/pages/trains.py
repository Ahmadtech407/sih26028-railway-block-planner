"""
Find Trains & Timetables Page.
Dedicated discovery experience for searching trains, schedules, departure/arrival times, and routes.
"""

from datetime import date
import streamlit as st

from ui.theme import clean_html
from ui.components.header import render_app_header
from ui.components.train_cards import render_train_card
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


def render_trains_page() -> None:
    """Render the train discovery and search page inspired by IRCTC & ConfirmTkt."""
    render_app_header()

    header_html = (
        '<div style="background: #101D37; border: 1px solid #2A3B57; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.75rem;">'
        '  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">'
        '    <div>'
        '      <span class="rt-card-title">🔍 Search Trains Across Monitored Corridors</span>'
        '      <div style="font-size:0.8rem; color:#A9BAD3; margin-top:2px;">'
        '        Explore schedules, class availability, live fares, and ConfirmTkt prediction confidence.'
        '      </div>'
        '    </div>'
        '    <span class="rt-badge rt-badge-reference">IRCTC TIMETABLES</span>'
        '  </div>'
        '</div>'
    )
    st.markdown(clean_html(header_html), unsafe_allow_html=True)

    c1, c_swap, c2, c3 = st.columns([4, 1, 4, 3])

    default_from = st.session_state.get("passenger_from", "New Delhi (NDLS)")
    default_to = st.session_state.get("passenger_to", "Kanpur Central (CNB)")

    with c1:
        src = st.selectbox(
            "Source Station",
            STATION_OPTIONS,
            index=STATION_OPTIONS.index(default_from) if default_from in STATION_OPTIONS else 0,
            key="trains_from_select",
        )
    with c_swap:
        st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
        if st.button("⇄", key="trains_swap_btn", help="Swap Stations", use_container_width=True):
            st.session_state["passenger_from"] = default_to
            st.session_state["passenger_to"] = default_from
            st.rerun()
    with c2:
        dest = st.selectbox(
            "Destination Station",
            STATION_OPTIONS,
            index=STATION_OPTIONS.index(default_to) if default_to in STATION_OPTIONS else 1,
            key="trains_to_select",
        )
    with c3:
        j_date = st.date_input(
            "Travel Date",
            value=date.today(),
            key="trains_date_input",
        )

    col_q, col_s = st.columns([1, 1])
    with col_q:
        default_quota = st.session_state.get("passenger_quota", "General (GN)")
        quota_choice = st.pills(
            "Quota",
            ["General (GN)", "Tatkal (TQ)", "Ladies (LD)", "Sr. Citizen (SS)"],
            default=default_quota if default_quota in ["General (GN)", "Tatkal (TQ)", "Ladies (LD)", "Sr. Citizen (SS)"] else "General (GN)",
            key="trains_quota_pills",
        )
    with col_s:
        sort_choice = st.pills(
            "Sort By",
            ["⚡ Fastest", "🌅 Departure Time", "🎟️ Seat Availability"],
            default="⚡ Fastest",
            key="trains_sort_pills",
        )

    st_filter = st.text_input(
        "Search by Train Number or Name",
        placeholder="e.g. 22436, Vande Bharat, Rajdhani, Shram Shakti",
        key="trains_text_filter",
    )

    # Fetch available trains from backend/passenger services
    from passenger_app import fetch_sections, fetch_trains

    sections = fetch_sections()
    matched_trains = []

    # Map selected corridor to section
    sec_id = "KNP-PRYJ-SEC-B"
    if "Delhi" in src or "Jammu" in dest:
        sec_id = "NDLS-JAT"
    elif "Kanpur" in src or "Prayagraj" in dest:
        sec_id = "KNP-PRYJ-SEC-B"

    active_section = next((s for s in sections if s.get("section_id") == sec_id), None)
    if not active_section and sections:
        active_section = sections[0]

    all_trains = fetch_trains(active_section.get("section_id", "KNP-PRYJ-SEC-B") if active_section else "KNP-PRYJ-SEC-B")

    # Apply text filter if provided
    filter_query = st_filter.strip().lower()
    for t in all_trains:
        t_num = str(t.get("train_number", "")).lower()
        t_name = str(t.get("name", "")).lower()
        if not filter_query or (filter_query in t_num or filter_query in t_name):
            matched_trains.append(t)

    # Sort trains based on user choice
    if sort_choice == "⚡ Fastest":
        matched_trains.sort(key=lambda x: x.get("speed_kmph", 0), reverse=True)
    elif sort_choice == "🌅 Departure Time":
        matched_trains.sort(key=lambda x: x.get("entry_time", "99:99"))

    # Render Results Header
    count_badge = get_provenance_badge_html("REFERENCE DATA", source="INDIAN_RAILWAYS_TIMETABLE")
    res_header_html = (
        f'<div style="display: flex; justify-content: space-between; align-items: baseline; margin: 1.25rem 0 0.75rem 0;">'
        f'  <div style="font-size: 1.1rem; font-weight: 700; color: #F1F5F9;">'
        f'    Available Trains ({len(matched_trains)}) · Quota: <span style="color:#38BDF8;">{quota_choice}</span>'
        f'  </div>'
        f'  <div>{count_badge}</div>'
        f'</div>'
    )
    st.markdown(clean_html(res_header_html), unsafe_allow_html=True)

    if not matched_trains:
        st.info("No trains match your search criteria. Please adjust your source, destination, or train filter.")
    else:
        for idx, train in enumerate(matched_trains):
            def _track(n):
                from ui.routing import page_live_status
                st.switch_page(page_live_status)

            def _coach(n):
                from ui.routing import page_coach_position
                st.switch_page(page_coach_position)

            render_train_card(
                train,
                section=active_section,
                key_prefix=f"tr_{idx}",
                on_track_click=_track,
                on_coach_click=_coach,
            )


if __name__ == "__main__":
    from ui.theme import inject_custom_theme
    inject_custom_theme()
    render_trains_page()
