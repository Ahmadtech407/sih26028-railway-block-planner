"""
Data Provenance & Authenticity Badges.
Provides truthful, standardized visual indicators across the RailTrack platform.
"""

from typing import Optional
import html


PROVENANCE_CONFIGS = {
    "VERIFIED LIVE": {
        "class": "rt-badge-live",
        "icon": "🟢",
        "description": "Verified from live telemetry stream or authenticated field feed.",
    },
    "VERIFIED HISTORICAL": {
        "class": "rt-badge-historical",
        "icon": "🔵",
        "description": "Historical logged telemetry or verified timetable records.",
    },
    "REFERENCE DATA": {
        "class": "rt-badge-reference",
        "icon": "⚪",
        "description": "Published Indian Railways timetable or static infrastructure reference.",
    },
    "PREDICTED": {
        "class": "rt-badge-predicted",
        "icon": "🟣",
        "description": "Estimated via dead-reckoning kinematics or machine learning model.",
    },
    "DEMO DATA": {
        "class": "rt-badge-demo",
        "icon": "🟡",
        "description": "Simulated evaluation scenario for offline testing.",
    },
    "UNAVAILABLE": {
        "class": "rt-badge-unavailable",
        "icon": "🔴",
        "description": "Live feed not connected; field sensor offline or unauthorized.",
    },
}


def get_provenance_badge_html(
    status: str,
    source: Optional[str] = None,
    observed_at: Optional[str] = None,
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

    escaped_title = html.escape(title_text)
    escaped_status = html.escape(normalized_status)

    source_detail = ""
    if source:
        source_detail = f' <span style="font-weight:400; opacity:0.85;">· {html.escape(source)}</span>'

    return (
        f'<span class="rt-badge {badge_class}" title="{escaped_title}">'
        f'{icon} {escaped_status}{source_detail}'
        f'</span>'
    )
