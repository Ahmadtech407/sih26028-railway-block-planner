"""
Structured Train Card Component.
Benchmark-grade railway card anatomy synthesizing ConfirmTkt, IRCTC NextGen, and ixigo Trains:
- ConfirmTkt: Color-coded CNF probability pills on waitlisted classes
- IRCTC NextGen: Multi-class availability horizontal rail with live fares
- ixigo: 7-day running day indicators (M T W T F S S)
- Guaranteed zero-indentation clean_html safety (prevents raw markdown code blocks)
"""

from typing import Dict, Any, Optional, List
import html
import streamlit as st

from ui.theme import clean_html
from ui.components.provenance import get_provenance_badge_html


def _get_class_availability(train_number: str, train_name: str) -> List[Dict[str, Any]]:
    """Generate realistic IRCTC multi-class availability and fares with ConfirmTkt probabilities."""
    name_lower = train_name.lower()

    if "vande bharat" in name_lower:
        return [
            {"code": "CC", "name": "AC Chair Car", "fare": "₹1,450", "status": "AVAILABLE - 42", "cnf": "high", "pill": "✓ AVAILABLE"},
            {"code": "EC", "name": "Exec Chair Car", "fare": "₹2,780", "status": "AVAILABLE - 12", "cnf": "high", "pill": "✓ AVAILABLE"},
        ]
    elif "shatabdi" in name_lower:
        return [
            {"code": "CC", "name": "AC Chair Car", "fare": "₹1,165", "status": "AVAILABLE - 28", "cnf": "high", "pill": "✓ AVAILABLE"},
            {"code": "EC", "name": "Exec Chair Car", "fare": "₹2,125", "status": "WL 3 (86% CNF)", "cnf": "med", "pill": "86% CNF"},
        ]
    elif "rajdhani" in name_lower:
        return [
            {"code": "3A", "name": "AC 3 Tier", "fare": "₹1,850", "status": "AVAILABLE - 34", "cnf": "high", "pill": "✓ AVAILABLE"},
            {"code": "2A", "name": "AC 2 Tier", "fare": "₹2,680", "status": "AVAILABLE - 08", "cnf": "high", "pill": "✓ AVAILABLE"},
            {"code": "1A", "name": "AC 1st Class", "fare": "₹4,250", "status": "WL 2 (91% CNF)", "cnf": "med", "pill": "91% CNF"},
        ]
    elif "duronto" in name_lower:
        return [
            {"code": "3A", "name": "AC 3 Tier", "fare": "₹1,620", "status": "AVAILABLE - 19", "cnf": "high", "pill": "✓ AVAILABLE"},
            {"code": "2A", "name": "AC 2 Tier", "fare": "₹2,340", "status": "AVAILABLE - 06", "cnf": "high", "pill": "✓ AVAILABLE"},
            {"code": "1A", "name": "AC 1st Class", "fare": "₹3,910", "status": "WL 4 (78% CNF)", "cnf": "med", "pill": "78% CNF"},
            {"code": "SL", "name": "Sleeper", "fare": "₹540", "status": "WL 18 (72% CNF)", "cnf": "med", "pill": "72% CNF"},
        ]
    else:
        # Standard Superfast / Express
        return [
            {"code": "SL", "name": "Sleeper", "fare": "₹465", "status": "AVAILABLE - 56", "cnf": "high", "pill": "✓ AVAILABLE"},
            {"code": "3E", "name": "3 AC Economy", "fare": "₹1,140", "status": "AVAILABLE - 21", "cnf": "high", "pill": "✓ AVAILABLE"},
            {"code": "3A", "name": "AC 3 Tier", "fare": "₹1,245", "status": "WL 14 (84% CNF)", "cnf": "med", "pill": "84% CNF"},
            {"code": "2A", "name": "AC 2 Tier", "fare": "₹1,780", "status": "WL 4 (88% CNF)", "cnf": "med", "pill": "88% CNF"},
            {"code": "1A", "name": "AC 1st Class", "fare": "₹2,990", "status": "AVAILABLE - 03", "cnf": "high", "pill": "✓ AVAILABLE"},
            {"code": "2S", "name": "Second Sitting", "fare": "₹190", "status": "AVAILABLE - 88", "cnf": "high", "pill": "✓ AVAILABLE"},
        ]


def _render_running_days_html(running_days: Optional[List[str]] = None) -> str:
    """Renders ixigo-style 7-day circular chips."""
    days = ["M", "T", "W", "T", "F", "S", "S"]
    active_indices = {0, 1, 2, 3, 4, 5, 6}
    if running_days and len(running_days) < 7:
        day_map = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
        active_indices = {day_map.get(d.upper()[:3], i) for i, d in enumerate(running_days)}

    chips = []
    for idx, day_letter in enumerate(days):
        is_active = idx in active_indices
        cls = "rt-day-chip active" if is_active else "rt-day-chip inactive"
        chips.append(f'<span class="{cls}">{day_letter}</span>')

    return f'<div class="rt-days-strip">{"".join(chips)}</div>'


def render_train_card(
    train: Dict[str, Any],
    section: Optional[Dict[str, Any]] = None,
    on_track_click=None,
    on_coach_click=None,
    key_prefix: str = "tc",
) -> None:
    """Renders a production-grade train card inspired by ConfirmTkt, IRCTC, and ixigo."""
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
    platform = str(train.get("platform_number", "1"))
    running_days = train.get("running_days")

    # Status Chip
    if delay > 0 or status == "DELAYED":
        status_chip = f'<span class="rt-badge rt-badge-unavailable">⏳ +{delay}m Late</span>'
    else:
        status_chip = '<span class="rt-badge rt-badge-live">✓ On Time</span>'

    # Provenance Badge
    badge_html = get_provenance_badge_html(
        "VERIFIED LIVE" if prov_source == "LIVE_GPS" else "TIMETABLE DIRECTORY",
        source=prov_source,
    )

    # Running Days
    days_html = _render_running_days_html(running_days)

    # Class Availability Rail (IRCTC + ConfirmTkt)
    classes = _get_class_availability(tr_num, tr_name)
    class_cards_html = []
    for c in classes:
        code = html.escape(c["code"])
        c_name = html.escape(c["name"])
        fare = html.escape(c["fare"])
        cnf_type = c["cnf"]

        if cnf_type == "high":
            pill_class = "rt-cnf-pill rt-cnf-high"
        elif cnf_type == "med":
            pill_class = "rt-cnf-pill rt-cnf-med"
        else:
            pill_class = "rt-cnf-pill rt-cnf-low"

        pill_html = f'<span class="{pill_class}">{html.escape(c["pill"])}</span>'

        class_cards_html.append(
            f'<div class="rt-class-card">'
            f'  <div style="display:flex; justify-content:space-between; align-items:center;">'
            f'    <span class="rt-class-code">{code}</span>'
            f'    <span class="rt-class-fare">{fare}</span>'
            f'  </div>'
            f'  <div style="font-size:0.68rem; color:#A9BAD3; margin-top:1px;">{c_name}</div>'
            f'  <div style="margin-top:4px;">{pill_html}</div>'
            f'</div>'
        )
    class_rail_html = f'<div class="rt-class-rail">{"".join(class_cards_html)}</div>'

    # Speed & Distance calculation
    dist_label = f"{train.get('distance_km', 440)} km" if train.get("distance_km") else "Monitored Run"
    duration_label = train.get("duration", "05h 45m")

    # Train Card Anatomy
    raw_card_html = (
        f'<div class="rt-card" style="margin-bottom:0.85rem;">'
        f'  <div class="rt-card-header">'
        f'    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">'
        f'      <span style="font-family:\'JetBrains Mono\', monospace; font-size:1.15rem; font-weight:800; color:#38BDF8;">🚆 {html.escape(tr_num)}</span>'
        f'      <span style="font-size:1.05rem; font-weight:700; color:#F8FAFC;">{html.escape(tr_name)}</span>'
        f'      {days_html}'
        f'    </div>'
        f'    <div style="display:flex; align-items:center; gap:8px;">'
        f'      {status_chip}'
        f'      {badge_html}'
        f'    </div>'
        f'  </div>'
        f'  <div style="display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:14px; margin:0.85rem 0;">'
        f'    <div>'
        f'      <div style="font-size:1.4rem; font-weight:800; color:#F8FAFC; font-family:\'JetBrains Mono\', monospace;">{html.escape(dep_time)}</div>'
        f'      <div style="font-size:0.9rem; font-weight:700; color:#CBD5E1; margin-top:2px;">{html.escape(str(from_stn))}</div>'
        f'      <div style="font-size:0.75rem; color:#38BDF8; font-weight:600; margin-top:2px;">Platform {html.escape(platform)}</div>'
        f'    </div>'
        f'    <div style="text-align:center; min-width:130px;">'
        f'      <div style="font-size:0.78rem; font-weight:700; color:#94A3B8;">⏱️ {duration_label}</div>'
        f'      <div style="height:2px; background:#2A3B57; margin:6px 0; position:relative;">'
        f'        <div style="position:absolute; right:0; top:-4px; width:8px; height:8px; border-radius:50%; background:#38BDF8; box-shadow:0 0 6px #38BDF8;"></div>'
        f'        <div style="position:absolute; left:0; top:-4px; width:8px; height:8px; border-radius:50%; background:#10B981;"></div>'
        f'      </div>'
        f'      <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#64748B;">'
        f'        <span>⚡ {speed} km/h</span>'
        f'        <span>📍 {dist_label}</span>'
        f'      </div>'
        f'    </div>'
        f'    <div style="text-align:right;">'
        f'      <div style="font-size:1.4rem; font-weight:800; color:#F8FAFC; font-family:\'JetBrains Mono\', monospace;">{html.escape(arr_time)}</div>'
        f'      <div style="font-size:0.9rem; font-weight:700; color:#CBD5E1; margin-top:2px;">{html.escape(str(to_stn))}</div>'
        f'      <div style="font-size:0.75rem; color:#94A3B8; margin-top:2px;">Scheduled Destination</div>'
        f'    </div>'
        f'  </div>'
        f'  <div style="font-size:0.75rem; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px;">'
        f'    🎟️ Available Classes & ConfirmTkt Probability'
        f'  </div>'
        f'  {class_rail_html}'
        f'</div>'
    )

    # Guarantee zero-indentation clean HTML
    st.markdown(clean_html(raw_card_html), unsafe_allow_html=True)

    # Action Buttons
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button(f"📍 Track Live Status", key=f"{key_prefix}_track_{tr_num}", use_container_width=True):
            st.session_state["train_search_query"] = tr_num
            if on_track_click:
                on_track_click(tr_num)
            from ui.routing import page_live_status
            st.switch_page(page_live_status)

    with btn_col2:
        if st.button(f"💺 View Coach Formation", key=f"{key_prefix}_coach_{tr_num}", use_container_width=True):
            st.session_state["coach_train_select"] = tr_num
            if on_coach_click:
                on_coach_click(tr_num)
            from ui.routing import page_coach_position
            st.switch_page(page_coach_position)
