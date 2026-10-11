"""
RailTrack Data Provenance, Freshness & Integrity Architecture.
==============================================================
Provides transparent data classification, configurable freshness thresholds,
circuit breaker resiliency, and rigorous validation for railway systems (SIH26028).

Mandatory Anti-Fabrication Principles:
- Never invent live train positions, current delays, platform numbers, or PNR results.
- Never replace failed live requests with mock data while retaining 'Live' labels.
- Classify all data into official, verified external, derived, cached, synthetic, or unverified.
"""

from __future__ import annotations

import enum
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# 1. STANDARDIZED SOURCE & STATUS CLASSIFICATIONS
# ==============================================================================

class SourceType(str, enum.Enum):
    """Authoritative classification of data origin."""
    OFFICIAL = "official"                   # Authoritative railway or government source (e.g., CRIS/NTES with confirmed integration)
    VERIFIED_EXTERNAL = "verified_external" # Known external API with confirmed integration (e.g., Open-Meteo, IMD)
    DERIVED = "derived"                     # Calculated by RailTrack using documented physics or ML models
    CACHED = "cached"                       # Previously obtained real data that may exceed freshness thresholds
    SYNTHETIC = "synthetic"                 # Explicitly created for simulation, development, or offline benchmarking
    UNVERIFIED = "unverified"               # Source or authenticity cannot be established


class DataStatus(str, enum.Enum):
    """Operational status of the data payload."""
    LIVE = "live"                           # Actively receiving verified live updates within freshness window
    DELAYED = "delayed"                     # Live stream active but telemetry packet is delayed
    STALE = "stale"                         # Freshness threshold exceeded; retention allowed with clear notice
    OFFLINE = "offline"                     # Operating without remote connectivity; using local verifiable baseline
    PREDICTED = "predicted"                 # Model or kinematic estimate; not an official railway declaration
    SCHEDULED = "scheduled"                 # Official published timetable schedule; not real-time GPS tracking
    DEMO = "demo"                           # Simulated test scenario; not for operational decisions
    UNAVAILABLE = "unavailable"             # Live feed not connected, sensor offline, or provider returned no data
    ERROR = "error"                         # Provider request failed or returned contradictory data


# ==============================================================================
# 2. CONFIGURABLE FRESHNESS THRESHOLDS (Seconds)
# ==============================================================================

FRESHNESS_THRESHOLDS: Dict[str, int] = {
    "live_gps": 120,          # 2 minutes for active moving trains
    "live_telemetry": 180,    # 3 minutes for sectional block signals
    "weather": 900,           # 15 minutes for meteorological observations
    "predictions": 300,       # 5 minutes for dynamic ML ETA estimates
    "platforms": 600,         # 10 minutes for platform assignment status
    "timetables": 86400,      # 24 hours for official published schedules
    "pnr_session": 1800,      # 30 minutes for authenticated passenger session
}


# ==============================================================================
# 3. PROVENANCED RECORD ENVELOPE
# ==============================================================================

def create_provenanced_record(
    data: Optional[Any],
    source_name: str,
    source_type: SourceType | str,
    status: DataStatus | str,
    fetched_at: Optional[str] = None,
    source_timestamp: Optional[str] = None,
    is_stale: bool = False,
    last_successful_update: Optional[str] = None,
    limitations: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Constructs an envelope ensuring every data field carries traceable provenance.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    s_type = source_type.value if isinstance(source_type, SourceType) else str(source_type).lower()
    s_status = status.value if isinstance(status, DataStatus) else str(status).lower()

    return {
        "data": data,
        "source_name": source_name,
        "source_type": s_type,
        "status": s_status,
        "fetched_at": fetched_at or now_iso,
        "source_timestamp": source_timestamp,
        "is_stale": is_stale,
        "last_successful_update": last_successful_update or now_iso,
        "limitations": limitations,
        "request_id": request_id or str(uuid.uuid4()),
    }


# ==============================================================================
# 4. DATA VALIDATION GUARDS (Anti-Fabrication & Sanity Checks)
# ==============================================================================

def validate_train_kinematics(train_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates physical feasibility of train telemetry:
    - Speed must not exceed 160.0 km/h (Mission Raftaar maximum track speed).
    - Speed must not be negative.
    - Coordinates, if present, must lie within the Indian subcontinent (lat: 6.0-38.0, lon: 68.0-98.0).
    - Position chainage must be non-negative.
    """
    errors: List[str] = []
    speed = train_data.get("speed_kmph")
    if speed is not None:
        try:
            s_val = float(speed)
            if s_val < 0.0:
                errors.append(f"Negative speed detected: {s_val} km/h")
            elif s_val > 165.0:
                errors.append(f"Implausible speed exceeds physical limit: {s_val} km/h")
        except (ValueError, TypeError):
            errors.append(f"Malformed speed value: {speed}")

    lat = train_data.get("gps_lat")
    lon = train_data.get("gps_lon")
    if lat is not None and lon is not None:
        try:
            f_lat, f_lon = float(lat), float(lon)
            if not (6.0 <= f_lat <= 38.0 and 68.0 <= f_lon <= 98.0):
                errors.append(f"Coordinates outside Indian railway network: ({f_lat}, {f_lon})")
        except (ValueError, TypeError):
            errors.append(f"Malformed GPS coordinates: ({lat}, {lon})")

    pos = train_data.get("position_km")
    if pos is not None:
        try:
            if float(pos) < 0.0:
                errors.append(f"Negative track position: {pos} km")
        except (ValueError, TypeError):
            errors.append(f"Malformed track position: {pos}")

    return (len(errors) == 0, errors)


def validate_weather_parameters(weather_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates meteorological parameters for physical plausibility:
    - Temperature between -20°C and 55°C.
    - Humidity between 0% and 100%.
    - Wind speed between 0 and 200 km/h.
    - Visibility between 0.0 and 50.0 km.
    """
    errors: List[str] = []
    temp = weather_data.get("temperature_c")
    if temp is not None:
        try:
            if not (-20.0 <= float(temp) <= 55.0):
                errors.append(f"Plausibility error: Temperature {temp}°C out of range")
        except (ValueError, TypeError):
            errors.append(f"Invalid temperature: {temp}")

    hum = weather_data.get("humidity_pct")
    if hum is not None:
        try:
            if not (0.0 <= float(hum) <= 100.0):
                errors.append(f"Humidity {hum}% exceeds [0, 100] interval")
        except (ValueError, TypeError):
            errors.append(f"Invalid humidity: {hum}")

    wind = weather_data.get("wind_speed_kmph")
    if wind is not None:
        try:
            if not (0.0 <= float(wind) <= 200.0):
                errors.append(f"Wind speed {wind} km/h out of range")
        except (ValueError, TypeError):
            errors.append(f"Invalid wind speed: {wind}")

    vis = weather_data.get("visibility_km")
    if vis is not None:
        try:
            if not (0.0 <= float(vis) <= 50.0):
                errors.append(f"Visibility {vis} km out of range")
        except (ValueError, TypeError):
            errors.append(f"Invalid visibility: {vis}")

    return (len(errors) == 0, errors)


def validate_pnr_format(pnr: str) -> bool:
    """Strictly validates 10-digit numeric Indian Railways PNR format."""
    if not pnr or not isinstance(pnr, str):
        return False
    clean = pnr.strip()
    return len(clean) == 10 and clean.isdigit()


# ==============================================================================
# 5. RESILIENT CIRCUIT BREAKER FOR EXTERNAL INTEGRATIONS
# ==============================================================================

class CircuitBreaker:
    """
    Fail-fast circuit breaker preventing cascading timeouts when external providers are offline.
    """
    def __init__(self, failure_threshold: int = 3, reset_timeout_seconds: float = 20.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.is_open = False

    def can_execute(self) -> bool:
        if not self.is_open:
            return True
        # Check if cooling period elapsed
        if time.time() - self.last_failure_time > self.reset_timeout_seconds:
            self.is_open = False
            self.failure_count = 0
            return True
        return False

    def record_success(self) -> None:
        self.failure_count = 0
        self.is_open = False

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
