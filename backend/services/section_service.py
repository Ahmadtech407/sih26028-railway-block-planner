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
    "NDLS-CNB-SEC-A": {
        "section_id": "NDLS-CNB-SEC-A",
        "section_name": "New Delhi - Kanpur Central (Main Trunk)",
        "status": "CLEAR",
        "length_km": 440.0,
        "start_km": 0.0,
        "end_km": 440.0,
        "max_capacity_tph": 14,
        "signals": "AUTOMATIC_BLOCK_SIGNALING",
        "speed_limit_kmph": 130,
        "active_trains": [],
    },
    "PRYJ-DDU-SEC-A": {
        "section_id": "PRYJ-DDU-SEC-A",
        "section_name": "Prayagraj - Pt. Deen Dayal Upadhyaya Junction",
        "status": "CLEAR",
        "length_km": 151.0,
        "start_km": 634.0,
        "end_km": 785.0,
        "max_capacity_tph": 12,
        "signals": "AUTOMATIC_BLOCK_SIGNALING",
        "speed_limit_kmph": 130,
        "active_trains": [],
    },
    "NDLS-UMB-SEC-A": {
        "section_id": "NDLS-UMB-SEC-A",
        "section_name": "New Delhi - Ambala Cantt (Northern Line)",
        "status": "CLEAR",
        "length_km": 198.0,
        "start_km": 0.0,
        "end_km": 198.0,
        "max_capacity_tph": 12,
        "signals": "AUTOMATIC_BLOCK_SIGNALING",
        "speed_limit_kmph": 130,
        "active_trains": [],
    },
}

# Train Type Speed Restrictions (km/h)
TRAIN_TYPE_SPEED_LIMITS: Dict[str, float] = {
    "VANDE_BHARAT": 160.0,
    "RAJDHANI": 140.0,
    "SUPERFAST": 130.0,
    "EXPRESS": 110.0,
    "PASSENGER": 100.0,
    "FREIGHT": 75.0,
    "GOODS": 75.0,
    "DEFAULT": 110.0,
}

# Weather-induced Speed Caps (km/h)
WEATHER_SPEED_CAPS: Dict[str, float] = {
    "EXTREME": 60.0,
    "HIGH": 75.0,
    "FOG": 75.0,
    "MEDIUM": 100.0,
    "LOW": 160.0,
}


def get_effective_speed_limit(
    section_id: str,
    train_type: str = "EXPRESS",
    weather_risk: str = "LOW",
    tsr_kmph: Optional[float] = None,
) -> float:
    """
    Computes the authoritative minimum speed constraint:
    effective_max = min(section_limit, train_type_limit, weather_cap, tsr_limit)
    """
    sec = SECTION_DATABASE.get(section_id, {})
    sec_limit = float(sec.get("speed_limit_kmph", 130.0))
    train_limit = TRAIN_TYPE_SPEED_LIMITS.get(train_type.upper(), TRAIN_TYPE_SPEED_LIMITS["DEFAULT"])

    w_risk = weather_risk.upper()
    weather_cap = WEATHER_SPEED_CAPS.get("HIGH" if "FOG" in w_risk else w_risk, 160.0)

    constraints = [sec_limit, train_limit, weather_cap]
    if tsr_kmph is not None and float(tsr_kmph) > 0:
        constraints.append(float(tsr_kmph))

    return max(15.0, min(constraints))


def calculate_section_congestion(section_id: str, active_train_count: int) -> Tuple[str, float]:
    """
    Computes real-time congestion level and probability from section capacity and occupancy:
    occupancy = active_train_count / max_capacity_tph
    """
    sec = SECTION_DATABASE.get(section_id, {})
    capacity = max(1, int(sec.get("max_capacity_tph", 12)))
    occupancy = min(1.0, active_train_count / float(capacity))

    if occupancy >= 0.85:
        return "CRITICAL", round(occupancy, 2)
    elif occupancy >= 0.60:
        return "HIGH", round(occupancy, 2)
    elif occupancy >= 0.35:
        return "MEDIUM", round(occupancy, 2)
    else:
        return "LOW", round(max(0.05, occupancy), 2)


def get_all_sections() -> List[SectionInfo]:
    """Retrieve list of all active railway sections."""
    return [SectionInfo(**sec) for sec in SECTION_DATABASE.values()]


def get_section_by_id(section_id: str) -> Optional[SectionInfo]:
    """Retrieve details of a specific section."""
    data = SECTION_DATABASE.get(section_id)
    if data:
        return SectionInfo(**data)
    return None
