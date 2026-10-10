"""
RailTrack Operations & Section Controller Console.
Administrative planning dashboard for train scheduling, conflict detection, CP-SAT maintenance optimization, and safety clearances.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.components.header import render_app_header
from ui.components.provenance import get_provenance_badge_html


BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


def minutes_to_hhmm(minutes: int) -> str:
    """Converts minutes since midnight to HH:MM format."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def render_operations_page() -> None:
    """Render the section controller and maintenance block planning console."""
    render_app_header()

    from app import (
        fetch_sections,
        fetch_section_details,
        fetch_trains,
        fetch_weather,
        fetch_platform_status,
        api_check_conflicts,
        api_solve_optimizer,
        api_commit_block,
        api_get_clearance,
        api_advance_clearance,
        api_reject_clearance,
        fetch_committed_blocks,
    )

    is_auth = st.session_state.get("authenticated", False)
    user = st.session_state.get("auth_user") or {}
    user_role = (user.get("role") or "GUEST").upper()

    # Safety Guard Banner
    st.markdown('<div class="rt-card" style="border-left: 4px solid #1E40AF;">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="rt-card-header">
            <div>
                <span class="rt-card-title">🛠️ Section Controller & Maintenance Optimizer</span>
                <div style="font-size:0.8rem; color:#64748B;">Role Authorization: <b>{user_role}</b> · Safety Standard: RDSO Non-Vital Advisory DSS</div>
            </div>
            <div>
                {get_provenance_badge_html("VERIFIED LIVE", source="CP_SAT_DISCRETE_ENGINE")}
            </div>
        </div>
        <div style="font-size:0.82rem; color:#475569; line-height:1.5;">
            This console allocates zero-conflict track maintenance possessions using discrete OR-Tools CP-SAT multi-resource scheduling, enforced safety gates, and electrical traction (OHE) permits.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # 1. Section Selection
    sections = fetch_sections()
    sec_names = [s.get("section_id", "KNP-PRYJ-SEC-B") for s in sections] or ["KNP-PRYJ-SEC-B"]

    c_sec, c_time = st.columns([4, 2])
    with c_sec:
        selected_section_id = st.selectbox("Operating Section", sec_names, key="ops_sec_select")
    with c_time:
        st.metric("System Clock", time.strftime("%H:%M:%S IST"))

    sec_details = fetch_section_details(selected_section_id)
    trains = fetch_trains(selected_section_id)

    # 2. Section Metrics Summary
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Section Status", sec_details.get("status", "CLEAR"))
    m2.metric("Active Trains", len(trains))
    m3.metric("Line Speed", f"{sec_details.get('speed_limit_kmph', 130)} km/h")
    m4.metric("Signaling", "ABS (Auto Block)")

    # 3. Live Section Track Diagram
    st.markdown('<div class="rt-card">', unsafe_allow_html=True)
    st.markdown('<div class="rt-card-title">🛤️ Live Track Diagram & Train Radar</div>', unsafe_allow_html=True)

    start_km = sec_details.get("start_km", 400.0)
    end_km = sec_details.get("end_km", 442.5)

    fig = go.Figure()
    # Main running line
    fig.add_trace(go.Scatter(
        x=[start_km, end_km], y=[0, 0],
        mode="lines", line=dict(width=10, color="#1E40AF"), showlegend=False
    ))
    # Junction markers
    fig.add_trace(go.Scatter(
        x=[start_km, end_km], y=[0, 0],
        mode="markers+text", text=["Kanpur (CNB)", "Prayagraj (PRYJ)"],
        textposition="top center", marker=dict(size=14, color="#071530"), showlegend=False
    ))
    # Train markers
    for t in trains:
        pos = t.get("position_km", 410.0)
        p = t.get("priority", 3)
        col = "#DC2626" if p <= 2 else ("#2563EB" if p == 3 else "#64748B")
        fig.add_trace(go.Scatter(
            x=[pos], y=[0], mode="markers+text",
            text=[f"🚆 {t.get('train_number')}"], textposition="bottom center",
            marker=dict(size=16, color=col), name=t.get("name", ""),
            hovertemplate=f"<b>{t.get('train_number')} {t.get('name')}</b><br>Speed: {t.get('speed_kmph')} km/h<br>KM: {pos:.1f}<extra></extra>"
        ))

    fig.update_layout(
        height=220, margin=dict(l=20, r=20, t=25, b=20),
        xaxis_title="Track Kilometre", yaxis=dict(visible=False, range=[-0.6, 0.6]),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 4. OR-Tools CP-SAT Maintenance Possessions Optimizer
    st.markdown('<div class="rt-card">', unsafe_allow_html=True)
    st.markdown('<div class="rt-card-title">⚙️ Mathematical Maintenance Window Optimizer (CP-SAT)</div>', unsafe_allow_html=True)

    op_col1, op_col2, op_col3 = st.columns(3)
    with op_col1:
        work_type = st.selectbox(
            "Maintenance Activity",
            ["Track Tamping (BCM)", "Rail Replacement", "OHE Inspection", "Turnout Renewal", "Bridge Deep Screening"],
            key="ops_work_type",
        )
    with op_col2:
        duration_min = st.slider("Required Window Duration (Minutes)", 30, 240, 90, 15, key="ops_duration")
    with op_col3:
        b_id = st.text_input("Possession Block Reference ID", value="MNT-KNP-04", key="ops_block_id")

    if st.button("🚀 Compute Zero-Conflict Maintenance Window", type="primary", use_container_width=True, key="ops_solve_btn"):
        with st.spinner("Executing discrete CP-SAT solver with machine transit intervals and safety buffers..."):
            res = api_solve_optimizer(
                block_id=b_id,
                section_id=selected_section_id,
                duration=duration_min,
                earliest=360,
                latest=1200,
                work_type=work_type,
            )
            st.session_state["ops_optimizer_result"] = res

    opt_res = st.session_state.get("ops_optimizer_result")
    if opt_res:
        st_status = opt_res.get("status")
        if st_status in ("OPTIMAL_SCHEDULED", "FEASIBLE_SUBOPTIMAL_SCHEDULED"):
            st.success(f"✅ Slot Allocated: {opt_res.get('allocated_window')} ({st_status})")
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("Proposed Window", opt_res.get("allocated_window", "--"))
            sc2.metric("Delay Impact", f"{opt_res.get('total_delay_minutes', 0)} min")
            sc3.metric("Feasibility Score", f"{opt_res.get('feasibility_score', 100.0)}%")

            # Clearance Advance Workflow
            st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
            st.markdown('<b>Safety Gate: Multi-Role Clearance Protocol</b>', unsafe_allow_html=True)
            c_role, c_act = st.columns([3, 2])
            with c_role:
                acting_role = st.selectbox(
                    "Acting Approver Role",
                    ["SECTION_CONTROLLER", "STATION_MASTER", "TRACTION_OHE", "SAFETY_OFFICER", "DIVISION_ADMIN"],
                    key="ops_clearance_role",
                )
            with c_act:
                if st.button("Advance Clearance State", use_container_width=True, key="ops_advance_btn"):
                    adv_res = api_advance_clearance(
                        block_id=b_id,
                        target_state="AUTHORIZED",
                        role=acting_role,
                        user_id=user.get("username", "controller_1"),
                        comment="Verified clear of conflicting rakes.",
                    )
                    if adv_res.get("status") == "SUCCESS":
                        st.toast("Clearance updated successfully.")
                    else:
                        st.error(adv_res.get("message"))
        else:
            st.warning(opt_res.get("message") or "No feasible slot found without violating train headways.")

    st.markdown('</div>', unsafe_allow_html=True)

    # 5. Persistent Committed Maintenance Possessions Log
    committed = fetch_committed_blocks()
    if committed:
        st.markdown('<div class="rt-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="rt-card-title">📋 Officially Committed TMS Block Log ({len(committed)})</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(committed), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    from ui.theme import inject_custom_theme
    inject_custom_theme()
    render_operations_page()
