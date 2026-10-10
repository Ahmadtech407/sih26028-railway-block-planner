"""
Station Stepper / Timeline Component.
Where Is My Train style vertical station progression showing scheduled vs observed times,
delay deltas, platforms, and clean zero-indentation HTML.
"""

from typing import List, Dict, Any, Optional
import html
from ui.theme import clean_html


def render_station_stepper_html(
    stations: List[Dict[str, Any]],
    current_station_idx: int = 0,
    delay_min: int = 0,
) -> str:
    """Generate Where Is My Train style vertical station progression timeline."""
    if not stations:
        return clean_html(
            '<div class="rt-card" style="text-align:center; color:#64748B;">'
            'No station route information available.'
            '</div>'
        )

    steps_html = []
    for idx, stn in enumerate(stations):
        name = html.escape(stn.get("name", f"Station {idx+1}"))
        code = html.escape(stn.get("code", ""))
        km = stn.get("km", idx * 30.0)
        sch_arr = html.escape(stn.get("scheduled_arrival", "--:--"))
        sch_dep = html.escape(stn.get("scheduled_departure", "--:--"))
        platform = html.escape(str(stn.get("platform", "1")))

        if idx < current_station_idx:
            step_class = "rt-timeline-step passed"
            dot_content = "✓"
            status_badge = '<span class="rt-badge rt-badge-live" style="font-size:0.68rem; padding:1px 6px;">Departed</span>'
            time_block = f'<span>Dep: <b style="color:#10B981;">{sch_dep}</b></span>'
        elif idx == current_station_idx:
            step_class = "rt-timeline-step active"
            dot_content = "🚆"
            if delay_min > 0:
                status_badge = f'<span class="rt-badge rt-badge-unavailable" style="font-size:0.68rem; padding:1px 6px;">Current Station (+{delay_min}m)</span>'
            else:
                status_badge = '<span class="rt-badge rt-badge-live" style="font-size:0.68rem; padding:1px 6px;">Current Station (On Time)</span>'
            time_block = (
                f'<span>Arr: <b style="color:#F8FAFC;">{sch_arr}</b></span>'
                f'<span style="margin-left:8px;">Dep: <b style="color:#38BDF8;">{sch_dep}</b></span>'
            )
        else:
            step_class = "rt-timeline-step"
            dot_content = str(idx + 1)
            status_badge = '<span style="color:#64748B; font-size:0.72rem; font-weight:600;">Upcoming</span>'
            time_block = (
                f'<span>Arr: <b style="color:#CBD5E1;">{sch_arr}</b></span>'
                f'<span style="margin-left:8px;">Dep: <b style="color:#CBD5E1;">{sch_dep}</b></span>'
            )

        step_html = (
            f'<div class="{step_class}">'
            f'  <div class="rt-timeline-line"></div>'
            f'  <div class="rt-timeline-dot">{dot_content}</div>'
            f'  <div style="flex:1; min-width:0; padding-bottom:12px;">'
            f'    <div style="display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:4px;">'
            f'      <div>'
            f'        <span style="font-weight:700; font-size:0.95rem; color:#F8FAFC;">{name}</span>'
            f'        <span style="font-size:0.75rem; font-weight:600; color:#38BDF8; margin-left:4px;">({code})</span>'
            f'      </div>'
            f'      <div>{status_badge}</div>'
            f'    </div>'
            f'    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; font-size:0.75rem; color:#94A3B8; margin-top:4px;">'
            f'      <div>{time_block}</div>'
            f'      <div style="display:flex; gap:10px;">'
            f'        <span>PF <b style="color:#38BDF8;">#{platform}</b></span>'
            f'        <span><b style="color:#64748B;">{km:.1f} km</b></span>'
            f'      </div>'
            f'    </div>'
            f'  </div>'
            f'</div>'
        )
        steps_html.append(step_html)

    timeline_body = "".join(steps_html)
    card_html = (
        f'<div class="rt-card">'
        f'  <div class="rt-card-header">'
        f'    <span class="rt-card-title">📍 Station Progression & Timetable</span>'
        f'    <span class="rt-badge rt-badge-live">LIVE TRACKING</span>'
        f'  </div>'
        f'  <div style="padding:0.5rem 0.25rem;">'
        f'    {timeline_body}'
        f'  </div>'
        f'</div>'
    )

    return clean_html(card_html)

