"""
RailTrack Page 3 — Live Train Status & Journey Tracking.
Where Is My Train & ixigo style train tracking interface.
Provides balanced desktop layout (Station progression timeline on the left,
Route map & live telemetry on the right), stacking cleanly vertically on mobile.
Features delay metrics, platform confidence, weather conditions, and destination wake-up alarm.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import html
import plotly.graph_objects as go
import streamlit as st

from ui.components.header import render_app_header
from ui.components.provenance import get_provenance_badge_html
from ui.components.station_stepper import render_station_stepper_html


def render_live_status_page() -> None:
    """Render the dedicated Live Train Status tracking page."""
    render_app_header()

    from passenger_app import (
        fetch_sections,
        fetch_trains,
        destination_eta_minutes,
        delay_minutes,
        distance_to_next_station,
        next_station_distance,
        display_current_station,
        get_route_stations,
        should_trigger_alarm,
        render_destination_alarm,
        render_ringing_alarm,
        fetch_weather,
        fetch_platforms,
        MAP_LAYOUT,
        MAP_TRACE,
    )

    sections = fetch_sections()
    sec_id = "KNP-PRYJ-SEC-B"
    active_section = next((s for s in sections if s.get("section_id") == sec_id), None)
    if not active_section and sections:
        active_section = sections[0]

    all_trains = fetch_trains(active_section.get("section_id", "KNP-PRYJ-SEC-B") if active_section else "KNP-PRYJ-SEC-B")

    train_options = {f"{t.get('train_number')} - {t.get('name')}": t for t in all_trains}

    # Preselected train from search or navigation
    preselected_num = st.session_state.get("train_search_query") or st.session_state.get("selected_train_number", "")
    default_idx = 0
    if preselected_num:
        for idx, (label, t) in enumerate(train_options.items()):
            if str(t.get("train_number")) == str(preselected_num):
                default_idx = idx
                break

    st.markdown('<div class="rt-card" style="margin-bottom: 1.25rem;">', unsafe_allow_html=True)
    st.markdown('<div class="rt-card-title">📍 Live Train Running Status Radar</div>', unsafe_allow_html=True)

    c_select, c_refresh = st.columns([5, 1])
    with c_select:
        selected_label = st.selectbox(
            "Select Train by Number or Name",
            list(train_options.keys()) if train_options else ["No trains active in monitored section"],
            index=default_idx if train_options else 0,
            key="live_status_train_select",
        )
    with c_refresh:
        st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
        if st.button("🔄 Refresh", key="btn_refresh_live_status", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    if not train_options:
        st.warning("No active trains are currently reported in the monitored corridor.")
        return

    train = train_options[selected_label]
    tr_num = train.get("train_number", "")
    tr_name = train.get("name", "")
    speed = train.get("speed_kmph", 0)
    delay = delay_minutes(train)
    dest_eta = train.get("destination_eta_min")
    if dest_eta is None and active_section:
        dest_eta = destination_eta_minutes(train, active_section)

    dist_next = next_station_distance(train, active_section)
    curr_stn_label = display_current_station(train, active_section)
    next_stn_label = train.get("next_station", "Kanpur Central")

    prov_status = train.get("source", "SIMULATED")
    badge_label = "VERIFIED LIVE" if prov_status in ("LIVE_GPS", "GOVT_OF_INDIA_CRIS", "GOVT_CRIS_NTES") else ("PREDICTED" if prov_status == "KINEMATIC_DEAD_RECKONING" else "DEMO DATA")

    # 1. Real-time Telemetry Overview Bar
    st.markdown(
        f"""
        <div class="rt-card" style="margin-bottom: 1.25rem;">
            <div class="rt-card-header">
                <div>
                    <span style="font-size: 1.35rem; font-weight: 800; color: #0F172A;">🚆 {html.escape(str(tr_num))} {html.escape(str(tr_name))}</span>
                    <div style="font-size: 0.8rem; color: #64748B; margin-top: 2px;">
                        Route: <b>{html.escape(str(train.get('passenger_from', 'Origin')))} → {html.escape(str(train.get('passenger_to', 'Destination')))}</b>
                    </div>
                </div>
                <div>
                    {get_provenance_badge_html(badge_label, source=prov_status)}
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-top: 0.75rem;">
                <div class="rt-metric-pill">
                    <span class="rt-metric-label">Current Location</span>
                    <span class="rt-metric-val" style="font-size: 0.95rem; color: #0F172A;">{html.escape(str(curr_stn_label))}</span>
                </div>
                <div class="rt-metric-pill">
                    <span class="rt-metric-label">Next Station</span>
                    <span class="rt-metric-val" style="font-size: 0.95rem; color: #1E40AF;">{html.escape(str(next_stn_label))}</span>
                </div>
                <div class="rt-metric-pill">
                    <span class="rt-metric-label">Distance to Next</span>
                    <span class="rt-metric-val" style="font-size: 0.95rem;">{f"{dist_next} km" if dist_next is not None else "--"}</span>
                </div>
                <div class="rt-metric-pill">
                    <span class="rt-metric-label">Current Speed</span>
                    <span class="rt-metric-val" style="font-size: 0.95rem; color: #1E40AF;">{speed} km/h</span>
                </div>
                <div class="rt-metric-pill">
                    <span class="rt-metric-label">Running Delay</span>
                    <span class="rt-metric-val" style="font-size: 0.95rem; color: {'#DC2626' if delay > 0 else '#059669'};">
                        {'+' + str(delay) + ' min' if delay > 0 else 'On Time'}
                    </span>
                </div>
                <div class="rt-metric-pill">
                    <span class="rt-metric-label">Destination ETA</span>
                    <span class="rt-metric-val" style="font-size: 0.95rem; color: #059669;">
                        {str(dest_eta) + ' min' if dest_eta is not None else '--'}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Ringing Alarm Check
    alarm_enabled = st.session_state.get("dest_alarm_enabled", False)
    alarm_buffer = st.session_state.get("dest_alarm_buffer_min", 15)
    alarm_dismissed = st.session_state.get("dest_alarm_dismissed", False)
    snoozed_until = st.session_state.get("dest_alarm_snoozed_until", None)

    if should_trigger_alarm(alarm_enabled, dest_eta, alarm_buffer, alarm_dismissed, snoozed_until):
        render_ringing_alarm(train, dest_eta if dest_eta is not None else 8)

    # 3. Balanced Desktop Layout: Station Stepper on Left, Interactive Map on Right
    col_timeline, col_map = st.columns([1, 1.15])

    with col_timeline:
        st.markdown('<div style="font-size: 1.05rem; font-weight: 700; color: #0F172A; margin-bottom: 8px;">🚉 Station Progression Timeline</div>', unsafe_allow_html=True)
        stations = get_route_stations(active_section, train)
        cur_idx = 1 if len(stations) > 2 else 0
        from passenger_app import clean_html
        st.markdown(clean_html(render_station_stepper_html(stations, current_station_idx=cur_idx, delay_min=delay)), unsafe_allow_html=True)

    with col_map:
        st.markdown('<div style="font-size: 1.05rem; font-weight: 700; color: #0F172A; margin-bottom: 8px;">🗺️ Route Map & Live Radar</div>', unsafe_allow_html=True)

        # Plotly Map Construction
        raw_stops = train.get("intermediate_stops") or []
        covered_km = float(train.get("distance_covered_km") or train.get("position_km") or 0.0)

        map_stations = [
            {"name": "New Delhi", "lat": 28.6431, "lon": 77.2197, "km": 0.0},
            {"name": "Kanpur Central", "lat": 26.4539, "lon": 80.3508, "km": 440.0},
            {"name": "Prayagraj Jn", "lat": 25.4484, "lon": 81.8340, "km": 634.0},
            {"name": "Varanasi Jn", "lat": 25.3268, "lon": 82.9868, "km": 760.0},
        ]

        if "Jammu" in str(train.get("passenger_to", "")):
            map_stations = [
                {"name": "New Delhi", "lat": 28.6431, "lon": 77.2197, "km": 0.0},
                {"name": "Ambala Cantt", "lat": 30.3606, "lon": 76.8270, "km": 198.0},
                {"name": "Ludhiana Jn", "lat": 30.9010, "lon": 75.8573, "km": 312.0},
                {"name": "Jammu Tawi", "lat": 32.7060, "lon": 74.8800, "km": 588.0},
            ]

        # Calculate Train Coordinates
        gps_lat = train.get("gps_lat")
        gps_lon = train.get("gps_lon")
        if isinstance(gps_lat, (int, float)) and isinstance(gps_lon, (int, float)):
            t_lat = float(gps_lat)
            t_lon = float(gps_lon)
        else:
            tot_km = max(0.001, map_stations[-1]["km"] - map_stations[0]["km"])
            frac = max(0.0, min(1.0, covered_km / tot_km))
            seg_idx = min(len(map_stations) - 2, max(0, int(frac * (len(map_stations) - 1))))
            s1 = map_stations[seg_idx]
            s2 = map_stations[seg_idx + 1]
            sub_frac = (frac * (len(map_stations) - 1)) - seg_idx
            t_lat = s1["lat"] + (s2["lat"] - s1["lat"]) * sub_frac
            t_lon = s1["lon"] + (s2["lon"] - s1["lon"]) * sub_frac

        fig = go.Figure()

        # Route travelled
        fig.add_trace(
            MAP_TRACE(
                lat=[s["lat"] for s in map_stations[:cur_idx + 1]] + [t_lat],
                lon=[s["lon"] for s in map_stations[:cur_idx + 1]] + [t_lon],
                mode="lines",
                line={"color": "#16a34a", "width": 5},
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # Route remaining
        fig.add_trace(
            MAP_TRACE(
                lat=[t_lat] + [s["lat"] for s in map_stations[cur_idx:]],
                lon=[t_lon] + [s["lon"] for s in map_stations[cur_idx:]],
                mode="lines",
                line={"color": "#38bdf8", "width": 4},
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # Station markers
        fig.add_trace(
            MAP_TRACE(
                lat=[s["lat"] for s in map_stations],
                lon=[s["lon"] for s in map_stations],
                mode="markers+text",
                text=[s["name"] for s in map_stations],
                textposition="top right",
                textfont={"size": 10, "color": "#0F172A"},
                marker={"color": "#0284c7", "size": 9},
                showlegend=False,
            )
        )

        # Live train marker
        fig.add_trace(
            MAP_TRACE(
                lat=[t_lat],
                lon=[t_lon],
                mode="markers",
                marker={"color": "#DC2626", "size": 18},
                name="Train",
                text=[f"<b>{train.get('name', 'Train')}</b><br>{speed:.0f} km/h"],
                hoverinfo="text",
                showlegend=False,
            )
        )

        # Center map
        mid_lat = sum(s["lat"] for s in map_stations) / len(map_stations)
        mid_lon = sum(s["lon"] for s in map_stations) / len(map_stations)

        fig.update_layout(
            MAP_LAYOUT(
                center={"lat": mid_lat, "lon": mid_lon},
                zoom=5.5,
                height=340,
            )
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Weather & Destination Alarm Controls
        render_destination_alarm(train, active_section, dest_eta)


if __name__ == "__main__":
    from ui.theme import inject_custom_theme
    inject_custom_theme()
    render_live_status_page()
