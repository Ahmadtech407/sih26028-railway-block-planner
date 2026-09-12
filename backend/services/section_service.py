"""
Section Management Service.
Provides sectional metadata, live status, and topology bounds.
"""

from typing import List, Optional, Dict, Any
from backend.schemas.api_models import SectionInfo

SECTION_DATABASE: Dict[str, Dict[str, Any]] = {
    "KNP-PRYJ-SEC-B": {
        "section_id": "KNP-PRYJ-SEC-B",
        "section_name": "Kanpur Central - Prayagraj Junction (Down Line)",
        "status": "CLEAR",
        "length_km": 42.5,
        "start_km": 400.0,
        "end_km": 442.5,
        "max_capacity_tph": 12,
        "signals": "AUTOMATIC_BLOCK_SIGNALING",
        "speed_limit_kmph": 130,
        "active_trains": ["22436", "12302", "12802", "15018", "BCNA"],
    },
    "KNP-PRYJ-SEC-A": {
        "section_id": "KNP-PRYJ-SEC-A",
        "section_name": "Kanpur Central - Prayagraj Junction (Up Line)",
        "status": "CLEAR",
        "length_km": 42.5,
        "start_km": 400.0,
        "end_km": 442.5,
        "max_capacity_tph": 12,
        "signals": "AUTOMATIC_BLOCK_SIGNALING",
        "speed_limit_kmph": 130,
        "active_trains": [],
    },
    "LKO-KNP-SEC-A": {
        "section_id": "LKO-KNP-SEC-A",
        "section_name": "Lucknow Charbagh - Kanpur Central (Up Line)",
        "status": "CLEAR",
        "length_km": 82.0,
        "start_km": 300.0,
        "end_km": 382.0,
        "max_capacity_tph": 10,
        "signals": "CENTRALIZED_TRAFFIC_CONTROL",
        "speed_limit_kmph": 160,
        "active_trains": ["22435", "12229"],
    },
}


def get_all_sections() -> List[SectionInfo]:
    """Retrieve list of all active railway sections."""
    return [SectionInfo(**sec) for sec in SECTION_DATABASE.values()]


def get_section_by_id(section_id: str) -> Optional[SectionInfo]:
    """Retrieve details of a specific section."""
    data = SECTION_DATABASE.get(section_id)
    if data:
        return SectionInfo(**data)
    return None
