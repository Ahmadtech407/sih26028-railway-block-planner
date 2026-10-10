"""
Station Stepper / Timeline Component.
Where Is My Train style station progression showing scheduled vs observed times and platforms.
"""

from typing import List, Dict, Any, Optional
import html


def render_station_stepper_html(
    stations: List[Dict[str, Any]],
    current_station_idx: int = 0,
    delay_min: int = 0,
) -> str:
    """Generate Where Is My Train style vertical station progression timeline."""
    if not stations:
        return '<div class="rt-card" style="text-align:center; color:#64748B;">No station route information available.</div>'

    steps_html = ""
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
            status_text = '<span style="color:#059669; font-weight:700;">Departed</span>'
        elif idx == current_station_idx:
            step_class = "rt-timeline-step active"
            dot_content = "🚆"
            delay_str = f" (+{delay_min}m)" if delay_min > 0 else " (On Time)"
            status_text = f'<span style="color:#1E40AF; font-weight:800;">Current Station{delay_str}</span>'
        else:
            step_class = "rt-timeline-step"
            dot_content = str(idx + 1)
            status_text = '<span style="color:#64748B;">Upcoming</span>'

        steps_html += f"""
        <div class="{step_class}">
            <div class="rt-timeline-line"></div>
            <div class="rt-timeline-dot">{dot_content}</div>
            <div style="flex: 1; min-width: 0;">
                <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;">
                    <div>
                        <span style="font-weight: 700; font-size: 0.95rem; color: #0F172A;">{name}</span>
                        <span style="font-size: 0.75rem; font-weight: 600; color: #64748B; margin-left: 4px;">({code})</span>
                    </div>
                    <div>
                        {status_text}
                    </div>
                </div>
                <div style="display: flex; gap: 14px; font-size: 0.78rem; color: #475569; margin-top: 4px;">
                    <span>Arr: <b>{sch_arr}</b></span>
                    <span>Dep: <b>{sch_dep}</b></span>
                    <span>PF: <b style="color:#1E40AF;">#{platform}</b></span>
                    <span>Distance: <b>{km:.1f} km</b></span>
                </div>
            </div>
        </div>
        """

    return f"""
    <div class="rt-card">
        <div class="rt-card-header">
            <span class="rt-card-title">📍 Station Progression & Timetable</span>
            <span class="rt-badge rt-badge-live">LIVE TRACKING</span>
        </div>
        <div style="padding: 0.5rem 0.25rem;">
            {steps_html}
        </div>
    </div>
    """
