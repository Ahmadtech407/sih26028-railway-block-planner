"""
Functional Disruption Matrix & Incident Impact Service
======================================================
Converts real-time operational disruptions (OHE, signal, track blocks, weather)
into structured numerical features, speed caps, and delay penalty multipliers
consumed directly by the ML ETA pipeline and kinematics guardrails.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# In-memory registry of active track and network disruptions
# section_id -> list of active disruption dicts
_ACTIVE_DISRUPTIONS: Dict[str, List[Dict[str, Any]]] = {}


def add_disruption(
    section_id: str,
    incident_type: str,
    severity: str = "MEDIUM",
    description: str = "",
    speed_cap_kmph: Optional[float] = None,
    estimated_duration_min: int = 60,
) -> Dict[str, Any]:
    """Register an active operational disruption on a railway section."""
    incident = {
        "id": f"DIS-{int(time.time()*1000)%1000000}",
        "section_id": section_id,
        "incident_type": incident_type.upper(),
        "severity": severity.upper(),
        "description": description or f"{incident_type} active on {section_id}",
        "speed_cap_kmph": speed_cap_kmph,
        "estimated_duration_min": estimated_duration_min,
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": time.time() + (estimated_duration_min * 60),
    }
    if section_id not in _ACTIVE_DISRUPTIONS:
        _ACTIVE_DISRUPTIONS[section_id] = []
    _ACTIVE_DISRUPTIONS[section_id].append(incident)
    logger.info("Registered disruption on %s: %s (Severity: %s)", section_id, incident_type, severity)
    return incident


def clear_disruptions(section_id: Optional[str] = None) -> int:
    """Clear active disruptions for a section, or all disruptions if section_id is None."""
    global _ACTIVE_DISRUPTIONS
    if section_id:
        cleared = len(_ACTIVE_DISRUPTIONS.get(section_id, []))
        _ACTIVE_DISRUPTIONS[section_id] = []
        return cleared
    else:
        total = sum(len(v) for v in _ACTIVE_DISRUPTIONS.values())
        _ACTIVE_DISRUPTIONS.clear()
        return total


def get_active_disruptions(section_id: str) -> List[Dict[str, Any]]:
    """Retrieve all non-expired disruptions on a section."""
    now = time.time()
    incidents = _ACTIVE_DISRUPTIONS.get(section_id, [])
    # Filter out expired incidents
    valid = [inc for inc in incidents if inc.get("expires_at", float("inf")) > now]
    _ACTIVE_DISRUPTIONS[section_id] = valid
    return valid


def evaluate_disruption_matrix(
    section_id: str,
    weather_risk: str = "LOW",
    congestion_level: str = "LOW",
    preceding_delay_min: int = 0,
    has_platform_conflict: bool = False,
) -> Dict[str, Any]:
    """
    Computes a comprehensive disruption vector and travel time multiplier.
    Output features feed directly into the dynamic ETA ML model and kinematics guardrails.
    """
    incidents = get_active_disruptions(section_id)

    has_ohe = any(i["incident_type"] == "OHE_BREAKDOWN" or "OHE" in i["incident_type"] for i in incidents)
    has_signal = any(i["incident_type"] == "SIGNAL_FAILURE" or "SIGNAL" in i["incident_type"] for i in incidents)
    has_blockage = any(i["incident_type"] == "TRACK_BLOCKAGE" or "BLOCKAGE" in i["incident_type"] for i in incidents)
    has_maint = any(i["incident_type"] == "MAINTENANCE_BLOCK" or "MAINT" in i["incident_type"] for i in incidents)

    # Base penalty multiplier
    delay_multiplier = 1.0
    effective_speed_cap: Optional[float] = None
    severity_scores = []

    if has_blockage:
        delay_multiplier *= 2.0
        effective_speed_cap = min(effective_speed_cap or 999.0, 0.0)
        severity_scores.append(1.0)

    if has_signal:
        delay_multiplier *= 1.45
        effective_speed_cap = min(effective_speed_cap or 999.0, 25.0)  # caution/crawl on signal fail
        severity_scores.append(0.7)

    if has_ohe:
        delay_multiplier *= 1.30
        effective_speed_cap = min(effective_speed_cap or 999.0, 40.0)
        severity_scores.append(0.6)

    if has_maint:
        delay_multiplier *= 1.25
        effective_speed_cap = min(effective_speed_cap or 999.0, 45.0)
        severity_scores.append(0.5)

    # Weather hazard penalty
    w_upper = weather_risk.upper()
    if "EXTREME" in w_upper:
        delay_multiplier *= 1.35
        effective_speed_cap = min(effective_speed_cap or 999.0, 60.0)
        severity_scores.append(0.8)
    elif "HIGH" in w_upper or "FOG" in w_upper:
        delay_multiplier *= 1.15
        effective_speed_cap = min(effective_speed_cap or 999.0, 75.0)
        severity_scores.append(0.4)

    # Congestion & platform conflict penalty
    c_upper = congestion_level.upper()
    if "CRITICAL" in c_upper or "HIGH" in c_upper:
        delay_multiplier *= 1.20
        severity_scores.append(0.5)
    elif "MEDIUM" in c_upper:
        delay_multiplier *= 1.08

    if has_platform_conflict:
        delay_multiplier *= 1.15
        severity_scores.append(0.4)

    # Cumulative severity index (0.0 to 1.0)
    severity_index = min(1.0, max(severity_scores)) if severity_scores else 0.0

    return {
        "section_id": section_id,
        "active_incident_count": len(incidents),
        "has_ohe_failure": int(has_ohe),
        "has_signal_failure": int(has_signal),
        "has_track_blockage": int(has_blockage),
        "has_maintenance_block": int(has_maint),
        "has_platform_conflict": int(has_platform_conflict),
        "delay_multiplier": round(delay_multiplier, 3),
        "disruption_severity_index": round(severity_index, 2),
        "effective_speed_cap": effective_speed_cap,
        "effective_speed_cap_kmph": effective_speed_cap,
        "incidents": incidents,
    }
