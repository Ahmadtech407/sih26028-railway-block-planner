"""Weather and platform intelligence routes."""

from fastapi import APIRouter, Query

from backend.schemas.api_models import PlatformConflictResponse, PlatformStatusResponse, SectionWeather
from backend.services.platform_service import get_platform_conflict_response, get_platform_status
from backend.services.weather_service import get_section_weather

router = APIRouter(tags=["Weather & Platforms"])


@router.get("/weather/{section_id}", response_model=SectionWeather)
async def section_weather(section_id: str, work_type: str = Query("Rail Replacement")):
    return get_section_weather(section_id, work_type=work_type)


@router.get("/platforms/{section_id}", response_model=PlatformStatusResponse)
async def section_platforms(section_id: str):
    trains, conflicts = get_platform_status(section_id)
    assigned = {train.platform_number for train in trains if train.platform_number is not None}
    return {
        "section_id": section_id,
        "source": "CRIS_TMS",
        "platforms": trains,
        "conflicts": conflicts,
        "available_platforms": [number for number in range(1, 10) if number not in assigned],
    }


@router.post("/platforms/conflicts", response_model=PlatformConflictResponse)
async def platform_conflicts(section_id: str = Query("KNP-PRYJ-SEC-B"), train_number: str | None = None):
    return get_platform_conflict_response(section_id, train_number)