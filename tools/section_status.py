"""
Tool: Query Section Status

Retrieves real-time operational status and track occupation for a specific
railway section from the infrastructure database.
"""

import json
from data.railway_reference_db import SECTION_DB


def query_section_status(section_id: str) -> str:
    """Retrieves real-time operational status, topology, signal type, and
    active train list for a given track section.

    Args:
        section_id: The track section code (e.g., 'KNP-PRYJ-SEC-B').
    """
    if section_id in SECTION_DB:
        section = SECTION_DB[section_id]
        return json.dumps({
            "section_id": section_id,
            "section_name": section.get("section_name", "Unknown"),
            "status": section["status"],
            "length_km": section["length_km"],
            "max_capacity_tph": section["max_capacity_tph"],
            "signal_type": section.get("signals", "UNKNOWN"),
            "track_type": section.get("track_type", "UNKNOWN"),
            "speed_limit_kmph": section.get("speed_limit_kmph", "N/A"),
            "active_trains": section["active_trains"],
            "active_train_count": len(section["active_trains"]),
        }, indent=2)

    return json.dumps({
        "error": f"Section '{section_id}' not found in division topology.",
        "available_sections": list(SECTION_DB.keys()),
    })
