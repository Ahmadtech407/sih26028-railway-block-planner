"""
Section API Routes.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from backend.schemas.api_models import SectionInfo
from backend.services.section_service import get_all_sections, get_section_by_id

router = APIRouter(prefix="/sections", tags=["Sections & Topology"])


@router.get("", response_model=List[SectionInfo], summary="Get all track sections")
async def list_sections():
    """Retrieve operational details and topology bounds for all track sections."""
    return get_all_sections()


@router.get("/route/calculate", summary="Calculate railway corridor and kinematics")
async def calculate_route(
    origin: str = "New Delhi",
    destination: str = "Jammu Tawi",
    train_number: str = "22436",
    speed_kmph: float = 112.0,
    progress_pct: float = 50.0,
):
    """Dynamically resolve railway route, intermediate stops, distance, and kinematics."""
    from backend.services.station_network import resolve_station_route
    return resolve_station_route(origin, destination, train_number, speed_kmph, progress_pct)


@router.get("/{section_id}", response_model=SectionInfo, summary="Get section by ID")
async def retrieve_section(section_id: str):
    """Retrieve real-time status and signaling info for a specific track section."""
    section = get_section_by_id(section_id)
    if not section:
        raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found in topology database.")
    return section
