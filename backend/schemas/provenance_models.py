"""
Data Truth & Provenance Models.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Establishes an uncompromised truth contract:
- LIVE: Confirmed authenticated real-time external API/sensor feed.
- VERIFIED_STATIC: Grounded in official static timetable/rake records (e.g., CRIS/NTES verified rakes).
- CALCULATED: Derived mathematically (e.g., kinematic dead reckoning, headway interval calculation).
- SIMULATED: Synthesized demo movement, synthetic timetable, or calibrated testbed.
- STALE: Previously live or calculated data whose freshness threshold has expired.
- UNAVAILABLE: Data not connected or loaded for this asset.
- UNKNOWN: Unverifiable state.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DataStatusEnum(str, Enum):
    LIVE = "LIVE"
    VERIFIED_STATIC = "VERIFIED_STATIC"
    CALCULATED = "CALCULATED"
    SIMULATED = "SIMULATED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class ProvenanceMetadata(BaseModel):
    status: DataStatusEnum = Field(..., description="Truth rating of the associated data point")
    source_name: str = Field(..., description="Underlying provider or algorithm")
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence_score: float = Field(1.0, ge=0.0, le=1.0)
    truth_statement: str = Field(..., description="Human-readable disclosure of how this value was acquired")
    is_live_external: bool = Field(False, description="Strictly True ONLY if authenticated external API was reached")
