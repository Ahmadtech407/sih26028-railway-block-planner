"""
Data Provenance & Authenticity Badges.
Provides truthful, standardized visual indicators across the RailTrack platform.
Conforms strictly to Phase 3 transparent data architecture requirements.
"""

from typing import Optional
import html


PROVENANCE_CONFIGS = {
    "VERIFIED LIVE": {
        "class": "rt-badge-live",
        "icon": "🟢",
        "description": "Verified from live telemetry stream or authenticated field feed.",
    },
    "LIVE": {
        "class": "rt-badge-live",
        "icon": "🟢",
        "description": "Source verified live telemetry.",
    },
    "VERIFIED HISTORICAL": {
        "class": "rt-badge-historical",
        "icon": "🔵",
        "description": "Historical logged telemetry or verified timetable records.",
    },
    "CACHED": {
        "class": "rt-badge-historical",
        "icon": "⏱️",
        "description": "Cached data; previously obtained from upstream source.",
    },
    "REFERENCE DATA": {
        "class": "rt-badge-reference",
        "icon": "⚪",
        "description": "Published Indian Railways timetable or static infrastructure reference.",
    },
    "SCHEDULED": {
        "class": "rt-badge-reference",
        "icon": "🗓️",
        "description": "Official published timetable information; not live GPS tracking.",
    },
    "PREDICTED": {
        "class": "rt-badge-predicted",
        "icon": "🟣",
        "description": "Estimated via dead-reckoning kinematics or machine learning model. Not an official railway ETA.",
    },
    "CALCULATED": {
        "class": "rt-badge-predicted",
        "icon": "📐",
        "description": "Calculated via dead-reckoning kinematics; not direct GPS telemetry.",
    },
    "AI ADVISORY": {
        "class": "rt-badge-predicted",
        "icon": "🤖",
        "description": "Decision support optimizer recommendation; requires Section Controller manual authorization.",
    },
    "DEMO DATA": {
        "class": "rt-badge-demo",
        "icon": "🟡",
        "description": "Simulated evaluation scenario for offline testing; not for operational decisions.",
    },
    "DEMO": {
        "class": "rt-badge-demo",
        "icon": "🟡",
        "description": "Simulated data; not for operational decisions.",
    },
    "UNAVAILABLE": {
        "class": "rt-badge-unavailable",
        "icon": "🔴",
        "description": "Live feed not connected; field sensor offline or unauthorized.",
    },
    "STALE": {
        "class": "rt-badge-caution",
        "icon": "⚠️",
        "description": "Data has exceeded freshness threshold; may no longer reflect current track reality.",
    },
}


def get_provenance_badge_html(
    status: str,
    source: Optional[str] = None,
    observed_at: Optional[str] = None,
    is_stale: bool = False,
    limitations: Optional[str] = None,
) -> str:
    """Generate HTML badge for transparent data provenance."""
    normalized_status = status.upper().strip()
    config = PROVENANCE_CONFIGS.get(
        normalized_status,
        {
            "class": "rt-badge-reference",
            "icon": "ℹ️",
            "description": "System data source.",
        },
    )

    badge_class = config["class"]
    icon = config["icon"]
    title_text = config["description"]
    if source:
        title_text += f" Source: {source}."
    if observed_at:
        title_text += f" Observed: {observed_at}."
    if is_stale:
        badge_class = "rt-badge-caution"
        icon = "⚠️"
        title_text += " [STALE: Exceeded freshness threshold]"
    if limitations:
        title_text += f" Limitation: {limitations}"

    escaped_title = html.escape(title_text)
    display_status = f"{normalized_status} (STALE)" if is_stale else normalized_status
    escaped_status = html.escape(display_status)

    source_detail = ""
    if source:
        source_detail = f' <span style="font-weight:400; opacity:0.85;">· {html.escape(source)}</span>'

    return (
        f'<span class="rt-badge {badge_class}" title="{escaped_title}">'
        f'{icon} {escaped_status}{source_detail}'
        f'</span>'
    )


def format_truthful_provenance_label(
    status: str,
    source_name: Optional[str] = None,
    age_seconds: Optional[int] = None,
) -> str:
    """
    Format user-facing truthful status string strictly conforming to Phase 3 anti-fabrication standards:
    - 'LIVE — Source verified — Updated 45 seconds ago'
    - 'PREDICTED — Model estimate — Not an official ETA'
    - 'CACHED — Last updated 35 minutes ago'
    - 'SCHEDULED — Timetable information, not live tracking'
    - 'DEMO — Simulated data; not for operational decisions'
    - 'UNAVAILABLE — Live source did not respond'
    """
    status_up = status.upper().strip()
    if "LIVE" in status_up:
        age_str = f" — Updated {age_seconds}s ago" if age_seconds is not None else ""
        src_str = f" ({source_name})" if source_name else ""
        return f"LIVE — Source verified{src_str}{age_str}"
    elif "PREDICT" in status_up or "CALCULAT" in status_up:
        return "PREDICTED — Model estimate — Not an official ETA"
    elif "CACHE" in status_up:
        age_str = f" {age_seconds // 60}m ago" if age_seconds is not None else ""
        return f"CACHED — Last updated{age_str}"
    elif "SCHEDUL" in status_up or "TIMETABLE" in status_up:
        return "SCHEDULED — Timetable information, not live tracking"
    elif "DEMO" in status_up or "SIMULAT" in status_up:
        return "DEMO — Simulated data; not for operational decisions"
    else:
        return "UNAVAILABLE — Live source did not respond"
