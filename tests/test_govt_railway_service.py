"""
Tests for Government of India Railway Running Data Service & Adapters.
Verifies CRIS / NTES / data.gov.in integration, ingestion, and source labeling.
"""

from datetime import datetime, timezone
from backend.services import govt_railway_service
from backend.services.train_data_source import GovtRailwayDataSource, SimulatorDataSource
from backend.services.train_service import get_trains_for_section
from passenger_app import source_label


def test_govt_feed_initial_status():
    status = govt_railway_service.get_feed_status()
    assert isinstance(status, dict)
    assert "status" in status
    assert "provider" in status
    assert "configured" in status


def test_govt_feed_runtime_configuration():
    # Set test credentials
    result = govt_railway_service.configure_govt_feed(
        api_key="TEST_CRIS_API_KEY_SIH26028",
        provider="CRIS_NTES",
    )
    assert result["configured"] is True
    assert result["status"] == "CONNECTED"
    assert result["provider"] == "CRIS_NTES"


def test_direct_govt_telemetry_ingestion():
    # Ingest a real CRIS / RTIS live GPS locomotive observation
    now = datetime.now(timezone.utc).isoformat()
    raw_payload = {
        "train_number": "22436",
        "gps_lat": 26.4499,
        "gps_lon": 80.3319,
        "speed_kmph": 115.0,
        "direction": "UP",
        "position_km": 422.5,
        "section_id": "KNP-PRYJ-SEC-B",
        "current_station": "Kanpur Central (CNB)",
        "next_station": "Prayagraj Junction (PRYJ)",
        "delay_minutes": 0,
        "platform_number": 3,
        "data_source": "GOVT_OF_INDIA_CRIS",
        "timestamp": now,
    }
    ingested = govt_railway_service.ingest_direct_govt_telemetry(raw_payload)
    assert ingested["train_number"] == "22436"
    assert ingested["data_source"] == "GOVT_OF_INDIA_CRIS"
    assert ingested["speed_kmph"] == 115.0
    assert ingested["current_station"] == "Kanpur Central (CNB)"

    # Verify retrieval from cache
    status = govt_railway_service.fetch_live_train_status("22436")
    assert status is not None
    assert status["train_number"] == "22436"
    assert status["data_source"] == "GOVT_OF_INDIA_CRIS"


def test_govt_railway_data_source_adapter():
    # Verify adapter serves live Govt data when present
    ds = GovtRailwayDataSource()
    pos = ds.get_live_position("22436")
    assert pos is not None
    assert pos["train_number"] == "22436"
    assert pos.get("data_source") == "GOVT_OF_INDIA_CRIS"

    # Verify section trains pick up the live Govt feed
    trains = get_trains_for_section("KNP-PRYJ-SEC-B")
    t_22436 = next((t for t in trains if t.train_number == "22436"), None)
    assert t_22436 is not None
    assert t_22436.data_source == "GOVT_OF_INDIA_CRIS"


def test_passenger_source_label_for_govt_feeds():
    # Verify exact Government of India & RapidAPI data source presentation
    assert source_label("GOVT_OF_INDIA_CRIS") == "GOVT OF INDIA · CRIS / NTES LIVE FEED"
    assert source_label("GOVT_CRIS_NTES") == "GOVT OF INDIA · CRIS / NTES LIVE FEED"
    assert source_label("RAPIDAPI_IRCTC") == "RAPIDAPI · IRCTC LIVE FEED"
    assert source_label("RAPIDAPI") == "RAPIDAPI · IRCTC LIVE FEED"
    assert source_label("GOVT_OF_INDIA_DATA_GOV") == "GOVT OF INDIA · DATA.GOV.IN OGD FEED"
    assert source_label("DATA_GOV_IN") == "GOVT OF INDIA · DATA.GOV.IN OGD FEED"
    # Preserved backward compatibility
    assert source_label("LIVE_GPS") == "LIVE GPS DATA"
    assert source_label("SIMULATED") == "SIMULATED DEMO DATA"
    assert source_label("UNAVAILABLE") == "DATA SOURCE UNAVAILABLE"


def test_rapidapi_irctc_configuration_and_normalization():
    # 1. Configure RapidAPI
    status = govt_railway_service.configure_govt_feed(
        api_key="TEST_RAPIDAPI_KEY_IRCTC",
        provider="RAPIDAPI_IRCTC",
        api_url="https://irctc1.p.rapidapi.com/api/v1/liveTrainStatus",
    )
    assert status["configured"] is True
    assert status["status"] == "CONNECTED"
    assert status["provider"] == "RAPIDAPI_IRCTC"

    # 2. Test JSON Normalization
    mock_payload = {
        "status": True,
        "data": {
            "current_station_name": "Kanpur Central",
            "next_station_name": "Prayagraj Junction",
            "delay": 15,
            "speed": 110.0,
            "platform": 2,
            "latitude": 26.4499,
            "longitude": 80.3319,
            "position_km": 420.0,
        }
    }
    normalized = govt_railway_service._normalize_rapidapi_json(mock_payload, "22436")
    assert normalized["train_number"] == "22436"
    assert normalized["data_source"] == "RAPIDAPI_IRCTC"
    assert normalized["current_station"] == "Kanpur Central"
    assert normalized["next_station"] == "Prayagraj Junction"
    assert normalized["delay_minutes"] == 15
    assert normalized["platform_number"] == 2
