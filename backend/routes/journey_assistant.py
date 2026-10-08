"""
RailTrack AI Journey Assistant Route (SIH26028).
================================================
Exposes REST endpoints for natural-language journey queries,
deterministic candidate train searches, deadline buffer calculations,
and data provenance disclosures.

Strict Data Protection & Privacy Model:
- General journey search is 100% public (no PNR login required).
- Does NOT expose personalized coach/seat assignments.
- Rate-limited to protect inference resources.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.journey_assistant_service import (
    search_journey_assistant,
    parse_journey_intent,
    get_active_train_provider,
)
from backend.services.station_network import STATION_REGISTRY

router = APIRouter(prefix="/journey-assistant", tags=["AI Journey Assistant"])


class JourneySearchRequest(BaseModel):
    query: Optional[str] = Field(
        default="",
        description="Natural language passenger journey query (e.g. 'I need to reach Jammu from Delhi before 8 PM')",
    )
    origin: Optional[str] = Field(
        default=None,
        description="Optional manual origin station code or name override (e.g. 'NDLS' or 'New Delhi')",
    )
    destination: Optional[str] = Field(
        default=None,
        description="Optional manual destination station code or name override (e.g. 'JAT' or 'Jammu Tawi')",
    )
    travel_date: Optional[str] = Field(
        default=None,
        description="Optional travel date in YYYY-MM-DD format (IST)",
    )
    latest_arrival: Optional[str] = Field(
        default=None,
        description="Optional latest arrival deadline in HH:MM format (e.g. '20:00' or '8 PM')",
    )
    earliest_departure: Optional[str] = Field(
        default=None,
        description="Optional earliest acceptable departure in HH:MM format (e.g. '06:00' or '6 AM')",
    )


class JourneyParseRequest(BaseModel):
    query: str = Field(
        ...,
        description="Natural language request to parse into structured journey intent",
    )


@router.post("/search", summary="Search and rank trains with deadline feasibility & arrival buffers")
async def search_journey(request: JourneySearchRequest) -> Dict[str, Any]:
    """
    Main endpoint for passenger journey planning.
    Parses natural language query (or manual overrides), queries authentic train timetables,
    evaluates arrival buffers (buffer = deadline - expected_arrival), ranks options,
    and returns transparent recommendation with provenance disclosures.
    """
    try:
        result = search_journey_assistant(
            query=request.query or "",
            origin_override=request.origin,
            dest_override=request.destination,
            travel_date_override=request.travel_date,
            latest_arrival_override=request.latest_arrival,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while evaluating journey feasibility: {str(exc)}",
        )


@router.post("/parse", summary="Parse natural language query into structured journey intent")
async def parse_journey(request: JourneyParseRequest) -> Dict[str, Any]:
    """
    Parses a natural language query into structured origin, destination, travel date,
    and deadline without selecting a train.
    """
    try:
        intent = parse_journey_intent(request.query)
        return intent.to_dict()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse journey query: {str(exc)}",
        )


@router.get("/stations", summary="List registered railway stations for UI suggestions")
async def list_stations(query: Optional[str] = Query(default=None, description="Optional search filter")) -> List[Dict[str, Any]]:
    """
    Returns registered railway stations (code, name, state, zone) for autocomplete.
    """
    clean_q = (query or "").strip().lower()
    results = []
    for code, meta in STATION_REGISTRY.items():
        if not clean_q or clean_q in code.lower() or clean_q in meta.get("name", "").lower():
            results.append({
                "code": code,
                "name": meta.get("name"),
                "zone": meta.get("zone"),
                "state": meta.get("state"),
            })
    return sorted(results, key=lambda x: x["name"])
