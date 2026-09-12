"""
Train Tracking & Kinematics Routes.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Query

from backend.schemas.api_models import (
    TrainDetails,
    TrainPredictionRequest,
    TrainPredictionResponse,
    TrainTelemetryIngestRequest,
    TrainTelemetryIngestResponse,
)
from backend.services.train_service import (
    get_trains_for_section,
    get_train_by_number,
    predict_train_kinematics,
    ingest_train_telemetry,
    LIVE_TRAINS_DB,
)
from backend.services import supabase_train_store as supa_store

router = APIRouter(prefix="/trains", tags=["Trains & Telemetry"])


@router.get("", response_model=List[TrainDetails], summary="Get scheduled trains on a section")
async def list_trains(section_id: str = Query("KNP-PRYJ-SEC-B", description="Track section identifier")):
    """List all scheduled train paths, entry/exit times, and speeds for a section."""
    return get_trains_for_section(section_id)


@router.get("/{train_number}", response_model=TrainDetails, summary="Get train details by number")
async def retrieve_train(train_number: str):
    """Retrieve detailed schedule and telemetry info for a specific train."""
    train = get_train_by_number(train_number)
    if not train:
        raise HTTPException(status_code=404, detail=f"Train '{train_number}' not found.")
    return train


@router.post("/predict", response_model=TrainPredictionResponse, summary="Predict position & confidence decay")
async def predict_position(request: TrainPredictionRequest):
    """
    Computes dead-reckoning extrapolation and confidence degradation
    for a train during telemetry/GPS blackouts.
    """
    prediction = predict_train_kinematics(
        train_number=request.train_number,
        seconds_since_update=request.seconds_since_update,
    )
    if not prediction:
        raise HTTPException(status_code=404, detail=f"Train '{request.train_number}' not found.")
    return prediction


@router.post("/telemetry", response_model=TrainTelemetryIngestResponse, summary="Ingest GPS train telemetry")
async def ingest_telemetry(request: TrainTelemetryIngestRequest):
    try:
        result = ingest_train_telemetry(request)

        # Persist the real GPS record to Supabase for ML training
        try:
            supa_store.store_telemetry(
                train_number=request.train_number,
                section_id=request.section_id,
                position_km=request.position_km or 0.0,
                speed_kmph=request.speed_kmph,
                delay_minutes=0,
                gps_lat=request.gps_lat,
                gps_lon=request.gps_lon,
                data_source="LIVE_GPS",
            )
            # Record current platform assignment for change-detection
            existing = LIVE_TRAINS_DB.get(request.train_number, {})
            current_platform = existing.get("platform_number")
            if current_platform is not None:
                supa_store.store_platform_assignment(
                    train_number=request.train_number,
                    section_id=request.section_id,
                    platform_number=current_platform,
                )
        except Exception:
            pass  # Never let storage failure break the telemetry ingest

        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/govt-feed/status", summary="Get Government of India railway feed status")
async def govt_feed_status():
    """Check connectivity and configuration of CRIS / NTES / data.gov.in data source."""
    from backend.services import govt_railway_service
    return govt_railway_service.get_feed_status()



@router.post("/govt-feed/ingest", summary="Ingest live Government of India / RTIS telemetry")
async def ingest_govt_telemetry(payload: dict):
    """Accepts live observation pushed by Indian Railways TMS / RTIS locomotive GPS feed."""
    from backend.services import govt_railway_service
    try:
        return govt_railway_service.ingest_direct_govt_telemetry(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/live-status/{train_number}", summary="Get live train running status from Govt feed")
async def get_live_train_status(train_number: str):
    """Retrieve real-time running status from Government of India / CRIS feed for any train."""
    from backend.services import govt_railway_service
    status = govt_railway_service.fetch_live_train_status(train_number)
    if not status:
        # Fall back to train service details
        train = get_train_by_number(train_number)
        if not train:
            raise HTTPException(status_code=404, detail=f"Live running status for train '{train_number}' not found.")
        return train
    return status
