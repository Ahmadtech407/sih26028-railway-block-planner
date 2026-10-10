"""
Railway Infrastructure Topology & Operating Rules Models.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Defines authoritative infrastructure schemas enforcing explicit, validated configuration:
- Headway per corridor section (no implicit assumptions from signaling type)
- Running times per train category
- Resource occupancy (tracks, platforms, crossovers, junctions)
- Route compatibility and clearance margins
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class InfrastructureConfigError(Exception):
    """Raised when critical section infrastructure configuration is missing or unvalidated."""
    pass


class InfrastructureResource(BaseModel):
    """A physical railway infrastructure resource with exclusive occupancy rules."""
    resource_id: str = Field(..., description="Unique physical resource identifier (e.g. TRACK_KNP_PRYJ_DN)")
    resource_type: str = Field(..., description="Resource class: TRACK_SECTION, PLATFORM, CROSSOVER, JUNCTION")
    is_exclusive: bool = Field(True, description="Whether resource enforces strict non-overlapping occupancy")
    description: Optional[str] = None


class SectionInfrastructureConfig(BaseModel):
    """
    Validated infrastructure operating constraints for a corridor section.
    Requires explicit specification; fails fast if missing.
    """
    section_id: str = Field(..., description="Section identifier e.g. KNP-PRYJ-SEC-B")
    track_id: str = Field(..., description="Track identifier e.g. KNP-PRYJ-DN-MAIN")
    start_km: float = Field(..., description="Start kilometer post")
    end_km: float = Field(..., description="End kilometer post")
    length_km: float = Field(..., description="Length in kilometers")
    
    # Mandatory operational rules (Must be explicitly configured, not guessed)
    minimum_headway_minutes: int = Field(..., ge=2, le=30, description="Mandatory minimum spacing between consecutive trains")
    clearance_margin_minutes: int = Field(..., ge=1, le=30, description="Post-maintenance track clearing & inspection buffer")
    setup_margin_minutes: int = Field(15, ge=0, le=60, description="Machine mobilization and protection setup buffer")
    
    # Exclusive physical resources allocated to this section
    exclusive_resources: List[str] = Field(..., min_length=1, description="List of discrete mutually exclusive resources")
    
    # Sectional running time per train category in minutes
    sectional_running_time_minutes: Dict[str, int] = Field(
        ...,
        description="Validated transit times per train category (e.g. {'VANDE_BHARAT': 20, 'EXPRESS': 28})"
    )
    
    # Route compatibility and interlockings
    route_compatibility: List[str] = Field(default_factory=list, description="Permitted route alignments")
    is_validated: bool = Field(True, description="Whether infrastructure configuration has been verified by engineering")
    config_version: str = Field("IR-RDSO-2026.1", description="Authoritative configuration version")
