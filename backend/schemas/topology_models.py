"""
Railway Track Infrastructure & Topology Domain Models.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Provides structured multi-track modeling (UP, DOWN, COMMON, LOOP, SIDING, CROSSOVERS).
Infrastructure data is explicitly tagged as REFERENCE_TOPOLOGY / SIMULATED unless
authoritative engineering databases are connected.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrackTypeEnum(str, Enum):
    UP_LINE = "UP_LINE"
    DOWN_LINE = "DOWN_LINE"
    COMMON_LINE = "COMMON_LINE"
    LOOP_LINE = "LOOP_LINE"
    SIDING = "SIDING"


class TrackOccupancyStatusEnum(str, Enum):
    CLEAR = "CLEAR"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE_BLOCKED = "MAINTENANCE_BLOCKED"
    CAUTION_SPEED_RESTRICTED = "CAUTION_SPEED_RESTRICTED"


class TrackModel(BaseModel):
    track_id: str = Field(..., json_schema_extra={"example": "KNP-PRYJ-DN-MAIN"})
    track_name: str = Field(..., json_schema_extra={"example": "Down Main Line (Kanpur -> Prayagraj)"})
    track_type: TrackTypeEnum = TrackTypeEnum.DOWN_LINE
    direction: str = Field("DOWN", description="UP, DOWN, or BIDIRECTIONAL")
    start_km: float = Field(400.0, json_schema_extra={"example": 400.0})
    end_km: float = Field(442.5, json_schema_extra={"example": 442.5})
    max_speed_kmph: int = Field(130, json_schema_extra={"example": 130})
    status: TrackOccupancyStatusEnum = TrackOccupancyStatusEnum.CLEAR
    active_trains: List[str] = Field(default_factory=list)
    electrification_ohe_active: bool = True
    adjacent_track_ids: List[str] = Field(default_factory=list)


class CrossoverModel(BaseModel):
    crossover_id: str = Field(..., json_schema_extra={"example": "XOVER-KNP-410"})
    location_km: float = Field(410.5, json_schema_extra={"example": 410.5})
    connects_track_a: str = Field(..., json_schema_extra={"example": "KNP-PRYJ-UP-MAIN"})
    connects_track_b: str = Field(..., json_schema_extra={"example": "KNP-PRYJ-DN-MAIN"})
    max_diverging_speed_kmph: int = Field(30, json_schema_extra={"example": 30})
    status: str = Field("NORMAL", description="NORMAL (straight) or REVERSE (crossover)")


class SectionTopologyModel(BaseModel):
    section_id: str = Field(..., json_schema_extra={"example": "KNP-PRYJ-SEC-B"})
    topology_name: str = Field(..., json_schema_extra={"example": "Kanpur Central - Prayagraj Junction Double Track Corridor"})
    topology_provenance: str = Field(
        "DEMO_REFERENCE_TOPOLOGY",
        description="Explicit provenance: DEMO_REFERENCE_TOPOLOGY or VERIFIED_AUTHORITATIVE",
    )
    is_authoritative: bool = Field(False, description="True only when verified against official IR engineering database")
    tracks: List[TrackModel] = Field(default_factory=list)
    crossovers: List[CrossoverModel] = Field(default_factory=list)
    total_route_km: float = Field(42.5, json_schema_extra={"example": 42.5})
    signaling_system: str = Field("AUTOMATIC_BLOCK_SIGNALING", json_schema_extra={"example": "AUTOMATIC_BLOCK_SIGNALING"})


class InfrastructureCoexistenceRequest(BaseModel):
    section_id: str = Field("KNP-PRYJ-SEC-B", json_schema_extra={"example": "KNP-PRYJ-SEC-B"})
    target_track_id: str = Field("KNP-PRYJ-DN-MAIN", json_schema_extra={"example": "KNP-PRYJ-DN-MAIN"})
    start_min: int = Field(..., json_schema_extra={"example": 630})
    end_min: int = Field(..., json_schema_extra={"example": 750})
    requires_ohe_power_block: bool = Field(False, description="If True, power shutdown may affect adjacent tracks")


class InfrastructureCoexistenceResponse(BaseModel):
    section_id: str
    target_track_id: str
    safe_to_coexist: bool
    affected_tracks: List[str]
    conflicting_movements: List[Dict[str, Any]] = Field(default_factory=list)
    crossover_constraints: List[str] = Field(default_factory=list)
    coexistence_rationale: str
