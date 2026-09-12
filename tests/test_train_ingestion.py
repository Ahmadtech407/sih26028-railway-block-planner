"""Tests for railway telemetry ingestion, simulation, ETA, and freshness."""

from datetime import datetime, timezone

from backend.schemas.api_models import TrainDirectionEnum, TrainTelemetryIngestRequest
from backend.services.train_service import (
    STALE_AFTER_SECONDS,
    calculate_eta_minutes,
    get_trains_for_section,
    ingest_train_telemetry,
)


def test_simulator_provides_explicit_source_and_eta():
    train = next(iter(get_trains_for_section("KNP-PRYJ-SEC-B")))
    assert train.data_source in ("SIMULATED", "GOVT_OF_INDIA_CRIS", "GOVT_CRIS_NTES")
    assert train.telemetry_timestamp
    assert train.eta_minutes is not None
    assert train.next_station


def test_live_gps_ingestion_updates_position_and_eta():
    response = ingest_train_telemetry(TrainTelemetryIngestRequest(
        train_number="12302",
        section_id="KNP-PRYJ-SEC-B",
        gps_lat=26.45,
        gps_lon=80.33,
        timestamp=datetime.now(timezone.utc).isoformat(),
        speed_kmph=90,
        direction=TrainDirectionEnum.UP,
        current_station="Kanpur Central",
        next_station="Prayagraj Junction",
        position_km=430,
    ))
    train = next(t for t in get_trains_for_section("KNP-PRYJ-SEC-B") if t.train_number == "12302")
    assert response.status == "INGESTED"
    assert train.data_source == "LIVE_GPS"
    assert train.position_km == 430
    assert train.current_station == "Kanpur Central"
    assert train.next_station == "Prayagraj Junction"
    assert train.eta_minutes == calculate_eta_minutes(430, 90, TrainDirectionEnum.UP)
    assert not train.stale


def test_old_ingested_observation_is_marked_stale():
    old_timestamp = datetime.now(timezone.utc).timestamp() - STALE_AFTER_SECONDS - 1
    timestamp = datetime.fromtimestamp(old_timestamp, timezone.utc).isoformat()
    ingest_train_telemetry(TrainTelemetryIngestRequest(
        train_number="12802",
        section_id="KNP-PRYJ-SEC-B",
        gps_lat=26.45,
        gps_lon=80.33,
        timestamp=timestamp,
        speed_kmph=80,
        direction=TrainDirectionEnum.UP,
        position_km=410,
    ))
    train = next(t for t in get_trains_for_section("KNP-PRYJ-SEC-B") if t.train_number == "12802")
    assert train.data_source == "LIVE_GPS"
    assert train.stale
    assert train.data_age_seconds > STALE_AFTER_SECONDS