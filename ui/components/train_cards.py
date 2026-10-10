"""
Structured Train Card Component.
Displays timetable, live running status, duration, and direct actions.
"""

from typing import Dict, Any, Optional
import html
import streamlit as st
from ui.components.provenance import get_provenance_badge_html


def render_train_card(
    train: Dict[str, Any],
    section: Optional[Dict[str, Any]] = None,
    on_track_click=None,
    on_coach_click=None,
    key_prefix: str = "tc",
) -> None:
    """Renders a clean, structured railway train card inspired by ixigo/IRCTC."""
    tr_num = str(train.get("train_number", "00000"))
    tr_name = train.get("name", "Express Train")
    dep_time = train.get("entry_time", "--:--")
    arr_time = train.get("exit_time", "--:--")
    from_stn = train.get("passenger_from") or (section.get("start_station") if section else "Origin")
    to_stn = train.get("passenger_to") or (section.get("end_station") if section else "Destination")
    speed = train.get("speed_kmph", 0)
    delay = train.get("delay_minutes", 0)
    status = train.get("status", "ON TIME")
    prov_source = train.get("source", "REFERENCE_TIMETABLE")

    if delay > 0 or status == "DELAYED":
        status_chip = f'<span class="rt-badge rt-badge-unavailable">⏳ Delayed by {delay}m</span>'
    else:
        status_chip = '<span class="rt-badge rt-badge-live">✓ On Time</span>'

    badge_html = get_provenance_badge_html(
        "VERIFIED LIVE" if prov_source == "LIVE_GPS" else "REFERENCE DATA",
        source=prov_source,
    )

    card_html = f"""
    <div class="rt-card">
        <div class="rt-card-header">
            <div>
                <span style="font-size: 1.15rem; font-weight: 800; color: #0F172A;">🚆 {html.escape(tr_num)}</span>
                <span style="font-size: 1.0rem; font-weight: 700; color: #1E40AF; margin-left: 6px;">{html.escape(tr_name)}</span>
            </div>
            <div>
                {status_chip}
                {badge_html}
            </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px; margin: 0.75rem 0;">
            <div>
                <div style="font-size: 1.25rem; font-weight: 800; color: #0F172A;">{html.escape(dep_time)}</div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #334155;">{html.escape(str(from_stn))}</div>
                <div style="font-size: 0.72rem; color: #64748B;">Platform {html.escape(str(train.get('platform_number', '1')))}</div>
            </div>

            <div style="text-align: center; min-width: 100px;">
                <div style="font-size: 0.75rem; font-weight: 600; color: #64748B;">⚡ {speed} km/h</div>
                <div style="height: 2px; background: #CBD5E1; margin: 4px 0; position: relative;">
                    <div style="position: absolute; right: 0; top: -3px; width: 6px; height: 6px; border-radius: 50%; background: #1E40AF;"></div>
                </div>
                <div style="font-size: 0.7rem; color: #94A3B8;">Section Run</div>
            </div>

            <div style="text-align: right;">
                <div style="font-size: 1.25rem; font-weight: 800; color: #0F172A;">{html.escape(arr_time)}</div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #334155;">{html.escape(str(to_stn))}</div>
                <div style="font-size: 0.72rem; color: #64748B;">Destination</div>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button(f"📍 Track Live Status", key=f"{key_prefix}_track_{tr_num}", use_container_width=True):
            st.session_state["train_search_query"] = tr_num
            if on_track_click:
                on_track_click(tr_num)
            st.session_state["nav_destination"] = "Live Status"
            st.rerun()

    with btn_col2:
        if st.button(f"💺 View Coach Formation", key=f"{key_prefix}_coach_{tr_num}", use_container_width=True):
            st.session_state["coach_train_select"] = tr_num
            if on_coach_click:
                on_coach_click(tr_num)
            st.session_state["nav_destination"] = "Coach Position"
            st.rerun()
