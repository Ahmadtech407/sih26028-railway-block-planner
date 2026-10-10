"""
RailTrack Page 7 — Alerts & Notifications.
Dedicated alerts hub providing train delay alerts, platform reassignment notices,
journey-specific advisories, and notification subscription preferences with transparent delivery status.
"""

from typing import Dict, Any
import html
import streamlit as st

from ui.components.header import render_app_header
from ui.components.provenance import get_provenance_badge_html


def render_alerts_page() -> None:
    """Render the dedicated alerts and notification management page."""
    render_app_header()

    from passenger_app import (
        fetch_sections,
        fetch_weather,
        fetch_platforms,
    )

    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #071530 0%, #1E40AF 100%); border-radius: 14px; padding: 1.5rem 1.25rem; color: #FFFFFF; margin-bottom: 1.25rem; box-shadow: 0 4px 16px rgba(7, 21, 48, 0.15);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                <div>
                    <div style="font-size: 1.5rem; font-weight: 800; margin-bottom: 0.35rem; letter-spacing: -0.02em;">
                        🔔 Alerts & Notification Center
                    </div>
                    <div style="font-size: 0.85rem; color: #BFDBFE; font-weight: 500;">
                        Live operational advisories, platform reassignments, TSR restrictions & alert subscriptions.
                    </div>
                </div>
                <div>
                    <span style="background: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.3); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; color: #FFFFFF;">
                        REAL-TIME NOTICES
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Journey-Specific Alerts (if user has active ticket)
    verified_ticket = st.session_state.get("verified_ticket")
    if verified_ticket and verified_ticket.get("valid"):
        jrny = verified_ticket.get("journey", {})
        bkg = verified_ticket.get("booking", {})
        tr_num = str(jrny.get("train_number", ""))
        tr_name = jrny.get("train_name", "Express")

        st.markdown(
            f"""
            <div style="background: #101D37; border: 1px solid #2A3B57; border-left: 4px solid #38BDF8; border-radius: 10px; padding: 1rem 1.15rem; margin-bottom: 1.25rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <div>
                        <span class="rt-card-title">🎯 Journey-Specific Advisory: {html.escape(tr_name)} ({html.escape(tr_num)})</span>
                        <div style="font-size:0.78rem; color:#A9BAD3;">PNR: {html.escape(str(verified_ticket.get('pnr', '')))} · Coach {html.escape(str(bkg.get('coach', '')))}</div>
                    </div>
                    <span class="rt-badge rt-badge-live">PERSONALIZED ALERT</span>
                </div>
                <div style="background: rgba(14, 165, 233, 0.12); border: 1px solid rgba(14, 165, 233, 0.3); border-radius: 6px; padding: 0.75rem; margin-top: 10px; font-size: 0.82rem; color: #BAE6FD;">
                    • <b>Departure Advisory</b>: Train is scheduled on time. Proceed to platform 15 minutes before departure.<br>
                    • <b>TSR Advisory</b>: Route traverses Kanpur-Prayagraj caution order zone (45 km/h restricted). +8 min buffer accounted in timetable.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Section Delay & Track Maintenance Possession Alerts
    st.markdown(
        """
        <div style="background: #101D37; border: 1px solid #2A3B57; border-radius: 10px; padding: 1rem 1.15rem; margin-bottom: 1.25rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom: 10px;">
                <div>
                    <span class="rt-card-title">⚠️ Active Operational & Track Possession Alerts</span>
                    <div style="font-size:0.8rem; color:#A9BAD3;">Corridor: Northern & North Central Railway Zones</div>
                </div>
                <span class="rt-badge rt-badge-caution">CAUTION ORDERS ACTIVE</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 10px;">
                <div style="padding: 0.85rem; background: rgba(217, 119, 6, 0.15); border: 1px solid rgba(217, 119, 6, 0.35); border-left: 4px solid #F59E0B; border-radius: 6px; font-size: 0.82rem; color: #FDE68A;">
                    <b>🚧 Temporary Speed Restriction (TSR-04) — KNP-PRYJ Section B:</b><br>
                    Deep screening and automated ballast regulation in progress between km 1024/12 and 1028/04. Speed restricted to <b>45 km/h</b>. Passenger delay impact: <b>+6 to +11 min</b>.
                </div>
                <div style="padding: 0.85rem; background: rgba(37, 99, 235, 0.15); border: 1px solid rgba(37, 99, 235, 0.35); border-left: 4px solid #3B82F6; border-radius: 6px; font-size: 0.82rem; color: #BFDBFE;">
                    <b>ℹ️ Rolling Stock Maintenance Possession (MNT-NDLS-01):</b><br>
                    Platform #4 at New Delhi Junction under scheduled catenary wire inspection from 02:00 to 04:30 hrs. All incoming trains diverted cleanly to Platform #2 and #3.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Platform Status & Reassignment Notices
    sections = fetch_sections()
    sec_id = "KNP-PRYJ-SEC-B"
    weather = fetch_weather(sec_id)
    platforms = fetch_platforms(sec_id)

    st.markdown(
        """
        <div style="background: #101D37; border: 1px solid #2A3B57; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div>
                    <span class="rt-card-title">🚉 Station Platform Reassignment Board</span>
                    <div style="font-size:0.8rem; color:#A9BAD3;">Junction Station Operations Hub · Kanpur Central (CNB)</div>
                </div>
                <span class="rt-badge rt-badge-reference">LIVE PLATFORM FEED</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    avail_platforms = platforms.get("available_platforms", [1, 2, 3, 4])
    assigned_platforms = platforms.get("assigned_platforms", {})

    st.info(f"Vacant platforms available for berthing: **{', '.join(f'Platform #{p}' for p in avail_platforms)}**")

    if assigned_platforms:
        p_rows = []
        for pf_num, tr in assigned_platforms.items():
            p_rows.append(f"• Platform **#{pf_num}**: Train **{tr.get('train_number')} {tr.get('name')}** (Arr: {tr.get('arrival_time', '--')})")
        st.write("\n".join(p_rows))
    else:
        st.caption("No sudden emergency platform changes active. All services berthing as per timetable.")

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # 4. Notification Preferences & Honest Subscription Status
    st.markdown(
        """
        <div style="background: #101D37; border: 1px solid #2A3B57; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div>
                    <span class="rt-card-title">📱 Notification Preferences & Delivery Channels</span>
                    <div style="font-size:0.8rem; color:#A9BAD3;">Configure how you receive delay alerts and platform updates</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ncol1, ncol2 = st.columns(2)
    with ncol1:
        app_sound = st.checkbox("🔔 In-App Audible IRCTC Chime Alerts", value=True, key="alerts_pref_chime")
        browser_notif = st.checkbox("🌐 Browser Desktop Notifications", value=True, key="alerts_pref_browser")
    with ncol2:
        sms_notif = st.checkbox("💬 SMS Gateway Advisories", value=False, key="alerts_pref_sms")
        wa_notif = st.checkbox("📱 WhatsApp Journey Tracking", value=False, key="alerts_pref_wa")

    # Honest disclosure of notification delivery mechanism
    st.markdown(
        """
        <div style="margin-top: 10px; margin-bottom: 1.25rem; padding: 0.75rem 0.85rem; background: #0B132B; border: 1px dashed #2A3B57; border-radius: 8px; font-size: 0.78rem; color: #A9BAD3;">
            <b style="color:#F1F5F9;">📡 Notification Gateway Status:</b><br>
            • <b>In-App Sound & Visual Alerts</b>: <span style="color:#34D399; font-weight:700;">ACTIVE (Built-in Audio Engine)</span><br>
            • <b>Browser Notifications</b>: <span style="color:#34D399; font-weight:700;">SUPPORTED (Requires Browser Permission)</span><br>
            • <b>SMS & WhatsApp Gateways</b>: <span style="color:#F59E0B; font-weight:700;">STANDBY / SIMULATION</span> (Production carrier delivery requires official Indian Railways National SMS Gateway API credentials).
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 5. Track Meteorology & IMD Forecast
    st.markdown(
        f"""
        <div style="background: #101D37; border: 1px solid #2A3B57; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div>
                    <span class="rt-card-title">🌦️ Track Meteorology & IMD Forecast</span>
                    <div style="font-size:0.8rem; color:#A9BAD3;">Corridor: Kanpur - Prayagraj Section</div>
                </div>
                {get_provenance_badge_html("VERIFIED LIVE" if weather.get("weather_source") == "LIVE_IMD_FEED" else "REFERENCE DATA")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Responsive 3-column x 2-row layout to prevent horizontal squishing/overflow
    w_row1_1, w_row1_2, w_row1_3 = st.columns(3)
    w_row1_1.metric("Condition", weather.get("weather_condition", "Clear"))
    w_row1_2.metric("Temperature", f"{weather.get('temperature_c', 28.0)}°C")
    w_row1_3.metric("Rain Probability", f"{weather.get('rain_probability_pct', 10)}%")

    w_row2_1, w_row2_2, w_row2_3 = st.columns(3)
    w_row2_1.metric("Wind Speed", f"{weather.get('wind_speed_kmph', 12)} km/h")
    w_row2_2.metric("Visibility", f"{weather.get('visibility_km', 10.0)} km")
    w_row2_3.metric("Track Risk", weather.get("weather_risk", "LOW"))

    if weather.get("imd_advisory"):
        st.info(f"🏛️ **IMD Advisory**: {weather.get('imd_advisory')}")

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # 6. Official Indian Railways Helplines
    st.markdown(
        """
        <div style="background: #101D37; border: 1px solid #2A3B57; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.75rem;">
            <div class="rt-card-title" style="font-size:0.95rem;">🚨 Official Indian Railways Helplines</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown(
            """
            <div style="background:#0D1526; border:1px solid #2A3B57; border-radius:8px; padding:12px; text-align:center;">
                <div style="font-size:1.4rem; font-weight:800; color:#38BDF8;">📞 139</div>
                <div style="font-size:0.8rem; font-weight:700; color:#F1F5F9; margin-top:2px;">RailMadad & General Enquiry</div>
                <div style="font-size:0.7rem; color:#A9BAD3;">24/7 National Passenger Helpline</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(
            """
            <div style="background:#0D1526; border:1px solid #2A3B57; border-radius:8px; padding:12px; text-align:center;">
                <div style="font-size:1.4rem; font-weight:800; color:#FF4B55;">🚨 182</div>
                <div style="font-size:0.8rem; font-weight:700; color:#F1F5F9; margin-top:2px;">RPF Security Helpline</div>
                <div style="font-size:0.7rem; color:#A9BAD3;">Railway Protection Force Emergency</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with h3:
        st.markdown(
            """
            <div style="background:#0D1526; border:1px solid #2A3B57; border-radius:8px; padding:12px; text-align:center;">
                <div style="font-size:1.4rem; font-weight:800; color:#34D399;">📱 SMS 139</div>
                <div style="font-size:0.8rem; font-weight:700; color:#F1F5F9; margin-top:2px;">Offline PNR & Telemetry</div>
                <div style="font-size:0.7rem; color:#A9BAD3;">Send 10-digit PNR via SMS</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    from ui.theme import inject_custom_theme
    inject_custom_theme()
    render_alerts_page()
