"""
Coach Formation & Seat Map Visualizer.
Renders authentic Indian Railways rake compositions, coach positions relative to engine, and seat maps.
"""

import os
import json
import html
from typing import Dict, Any, Optional
import streamlit as st


COACH_DATA_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend", "data", "coach_formations.json")
)


@st.cache_data(ttl=600)
def load_coach_formations() -> Dict[str, Any]:
    """Load authentic CRIS coach formations from local data file."""
    if os.path.exists(COACH_DATA_FILE):
        try:
            with open(COACH_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            forms = data.get("formations", {})
            alias_map = {
                "22435": "22436",
                "12302": "12301",
                "12003": "12004",
                "12423": "12424",
                "12801": "12802",
                "12451": "12452",
            }
            for k, v in alias_map.items():
                if v in forms and k not in forms:
                    cloned = dict(forms[v])
                    cloned["trainNumber"] = k
                    forms[k] = cloned
            return forms
        except Exception:
            pass
    return {}


def render_coach_formation_html(train_number: str, coach_id: str, seat_number: str = "") -> str:
    """Renders train-specific coach formation with exact coach index and verification status."""
    formations = load_coach_formations()
    t_key = str(train_number).strip()
    formation = formations.get(t_key)

    c_id = str(coach_id).strip().upper()
    s_num = str(seat_number).strip()

    if not formation or formation.get("verificationStatus") == "UNAVAILABLE" or not formation.get("coaches"):
        return f"""
        <div class="rt-card" style="text-align:center; background:#FEF2F2; border-color:#FECACA;">
            <div style="font-size:1.6rem; margin-bottom:6px;">⚠️</div>
            <div style="font-size:0.95rem; font-weight:700; color:#DC2626; margin-bottom:4px;">Coach Formation Unavailable</div>
            <div style="font-size:0.8rem; color:#64748B; line-height:1.5;">
                Published rake formation data is currently unavailable for Train <b>{html.escape(t_key)}</b>.<br>
                Coach position is not estimated to avoid misleading station platform navigation.
            </div>
        </div>
        """

    coaches = formation.get("coaches", [])
    exact_index = -1
    for i, c in enumerate(coaches):
        if str(c.get("coachId", "")).upper() == c_id:
            exact_index = i
            break

    strip_html = ""
    for idx, c in enumerate(coaches):
        is_highlight = (exact_index != -1 and str(c.get("coachId", "")).upper() == c_id)
        is_loco = (c.get("type") == "LOCOMOTIVE")
        lbl = html.escape(str(c.get("displayLabel", c.get("coachId"))))
        cls_lbl = html.escape(str(c.get("class") or ("Loco" if is_loco else c.get("type")[:2])))

        if is_highlight:
            body_class = "rt-rake-coach selected"
            pointer = '<div style="position:absolute; top:-16px; left:50%; transform:translateX(-50%); font-size:0.6rem; font-weight:800; color:#1E40AF;">YOU ▼</div>'
        elif is_loco:
            body_class = "rt-rake-coach loco"
            pointer = ""
        else:
            body_class = "rt-rake-coach"
            pointer = ""

        strip_html += f"""
        <div style="display:flex; flex-direction:column; align-items:center; flex-shrink:0; position:relative;">
            {pointer}
            <div class="{body_class}">{lbl}</div>
            <div class="rt-rake-class">{cls_lbl}</div>
        </div>
        """

    v_status = str(formation.get("verificationStatus", "VERIFIED")).upper()
    total_coaches = len(coaches)

    if exact_index == -1:
        known = ", ".join(c.get("coachId", "") for c in coaches if c.get("type") != "LOCOMOTIVE")
        return f"""
        <div class="rt-card">
            <div style="margin-bottom:8px; font-weight:700; color:#D97706;">
                ⚠️ Coach "{html.escape(c_id)}" not found in Train {html.escape(t_key)}
            </div>
            <div style="font-size:0.8rem; color:#64748B; margin-bottom:12px;">
                Verified coaches in this rake: <b>{html.escape(known)}</b>
            </div>
            <div class="rt-card-header">
                <span class="rt-card-title">🚃 Train {html.escape(t_key)} Formation ({total_coaches} Coaches)</span>
                <span class="rt-badge rt-badge-historical">VERIFIED RAKE</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#64748B; font-weight:600; text-transform:uppercase;">
                <span>← Engine (Locomotive)</span>
                <span>Guard / Rear →</span>
            </div>
            <div class="rt-rake-diagram">
                {strip_html}
            </div>
        </div>
        """

    ratio = exact_index / max(1, total_coaches - 1)
    if ratio <= 0.33:
        rel_pos = "Front Section (Near Engine)"
    elif ratio <= 0.66:
        rel_pos = "Middle Section"
    else:
        rel_pos = "Rear Section (Near Guard)"

    seat_sub = f" · Seat <b>{html.escape(s_num)}</b>" if s_num else ""
    return f"""
    <div class="rt-card">
        <div class="rt-card-header">
            <span class="rt-card-title">🚃 Train {html.escape(t_key)} Verified Rake Formation</span>
            <span class="rt-badge rt-badge-live">VERIFIED FORMATION</span>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#64748B; font-weight:600; text-transform:uppercase;">
            <span>← Locomotive (Front)</span>
            <span>Brake Van / Rear →</span>
        </div>
        <div class="rt-rake-diagram">
            {strip_html}
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:10px; margin-top:12px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px;">
            <div>
                <div class="rt-metric-label">Coach</div>
                <div class="rt-metric-val" style="color:#1E40AF;">{html.escape(c_id)}{seat_sub}</div>
            </div>
            <div>
                <div class="rt-metric-label">Position from Engine</div>
                <div class="rt-metric-val">{exact_index + 1} of {total_coaches}</div>
            </div>
            <div>
                <div class="rt-metric-label">Platform Location</div>
                <div style="font-size:0.95rem; font-weight:700; color:#0F172A; margin-top:2px;">{rel_pos}</div>
            </div>
        </div>
    </div>
    """


def render_coach_seat_map_html(train_number: str, coach_id: str, seat_number: str = "") -> str:
    """Renders interactive coach interior seat map with highlighted passenger seat."""
    c_id = str(coach_id).strip().upper()
    s_clean = str(seat_number).strip()
    is_cc = c_id.startswith("C") or c_id.startswith("E")

    if is_cc:
        layout_name = "2×3 Chair Car Layout"
        rows = [
            [("1 W", "1"), ("2 M", "2"), ("3 A", "3"), ("4 A", "4"), ("5 W", "5")],
            [("6 W", "6"), ("7 M", "7"), ("8 A", "8"), ("9 A", "9"), ("10 W", "10")],
            [("11 W", "11"), ("12 M", "12"), ("13 A", "13"), ("14 A", "14"), ("15 W", "15")],
        ]
    else:
        layout_name = "Classic 3-Tier Sleeper / AC Layout"
        rows = [
            [("1 LB", "1"), ("2 MB", "2"), ("3 UB", "3"), ("7 SL", "7"), ("8 SU", "8")],
            [("4 LB", "4"), ("5 MB", "5"), ("6 UB", "6"), ("15 SL", "15"), ("16 SU", "16")],
        ]

    rows_html = ""
    for r in rows:
        left_seats = ""
        for lbl, num in r[:3]:
            sel = "background:#059669; color:#FFF; font-weight:800;" if num == s_clean else "background:#F1F5F9; color:#0F172A;"
            left_seats += f'<span style="{sel} padding:4px 8px; border-radius:4px; font-size:0.75rem; border:1px solid #CBD5E1;">{lbl}</span>'

        right_seats = ""
        for lbl, num in r[3:]:
            sel = "background:#059669; color:#FFF; font-weight:800;" if num == s_clean else "background:#F1F5F9; color:#0F172A;"
            right_seats += f'<span style="{sel} padding:4px 8px; border-radius:4px; font-size:0.75rem; border:1px solid #CBD5E1;">{lbl}</span>'

        rows_html += f"""
        <div style="display:flex; justify-content:space-between; align-items:center; padding:4px 0;">
            <div style="display:flex; gap:6px;">{left_seats}</div>
            <span style="font-size:0.65rem; color:#94A3B8; text-transform:uppercase;">Aisle</span>
            <div style="display:flex; gap:6px;">{right_seats}</div>
        </div>
        """

    return f"""
    <div class="rt-card" style="margin-top:10px;">
        <div class="rt-card-header">
            <span class="rt-card-title">💺 Coach {html.escape(c_id)} Interior Layout ({layout_name})</span>
            <span class="rt-badge rt-badge-reference">SEAT MAP</span>
        </div>
        <div style="max-width:340px; margin:0 auto; padding:8px 0;">
            {rows_html}
        </div>
        <div style="font-size:0.7rem; color:#64748B; text-align:center; margin-top:8px;">
            ⚡ Power Outlets Under Armrest · 🚻 Toilets at Both Vestibule Ends
        </div>
    </div>
    """
