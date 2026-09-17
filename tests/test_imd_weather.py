"""
Unit and integration tests for IMD (India Meteorological Department) Weather Integration.

Validates:
- Official IMD station resolution across Indian Railways corridor sections.
- IMD 4-tier operational safety color-code computation (Green, Yellow, Orange, Red).
- Seamless fallback resilience when external network requests fail.
- FastAPI REST endpoint /api/weather/{section_id} returning valid IMD fields.
"""

from unittest.mock import patch
import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.services.weather_service import (
    IMD_STATION_MAP,
    calculate_imd_alert,
    get_section_weather,
    _WEATHER_CACHE,
)


def test_imd_station_mapping():
    """Verify that IR corridor sections map to valid official IMD station IDs."""
    assert "KNP-PRYJ-SEC-B" in IMD_STATION_MAP
    imd_id, imd_name = IMD_STATION_MAP["KNP-PRYJ-SEC-B"]
    assert imd_id == "IMD-42452"
    assert "Kanpur" in imd_name

    assert "NDLS-CNB-SEC-A" in IMD_STATION_MAP
    delhi_id, delhi_name = IMD_STATION_MAP["NDLS-CNB-SEC-A"]
    assert delhi_id == "IMD-42182"
    assert "New Delhi" in delhi_name


def test_calculate_imd_alert_tiers():
    """Verify official IMD 4-stage operational color warnings."""
    # 1. Green: Normal / No Warning
    color, level, advisory = calculate_imd_alert(rain_prob=10, rain_intensity=0.0, wind_speed=10.0, visibility_km=8.0)
    assert color == "GREEN"
    assert level == "NO_WARNING"
    assert "Favorable meteorological conditions" in advisory

    # 2. Yellow: Watch / Be Updated (moderate rain or brisk wind)
    color_y, level_y, advisory_y = calculate_imd_alert(rain_prob=45, rain_intensity=2.0, wind_speed=25.0, visibility_km=5.0)
    assert color_y == "YELLOW"
    assert level_y == "WATCH"
    assert "WATCH" in advisory_y

    # 3. Orange: Alert / Be Prepared (heavy rain, strong wind, or thick fog)
    color_o, level_o, advisory_o = calculate_imd_alert(rain_prob=80, rain_intensity=8.0, wind_speed=45.0, visibility_km=1.5)
    assert color_o == "ORANGE"
    assert level_o == "ALERT"
    assert "ALERT" in advisory_o

    # 4. Red: Warning / Take Action (severe downpour, gale-force winds, or dense fog)
    color_r, level_r, advisory_r = calculate_imd_alert(rain_prob=95, rain_intensity=25.0, wind_speed=70.0, visibility_km=0.3)
    assert color_r == "RED"
    assert level_r == "WARNING"
    assert "RED WARNING" in advisory_r


def test_get_section_weather_returns_imd_fields():
    """Verify get_section_weather populates all official IMD fields."""
    _WEATHER_CACHE.clear()
    weather = get_section_weather("KNP-PRYJ-SEC-B")

    assert weather is not None
    assert hasattr(weather, "imd_color_code")
    assert weather.imd_color_code in {"GREEN", "YELLOW", "ORANGE", "RED"}
    assert hasattr(weather, "imd_alert_level")
    assert weather.imd_alert_level in {"NO_WARNING", "WATCH", "ALERT", "WARNING"}
    assert hasattr(weather, "imd_station_id")
    assert weather.imd_station_id.startswith("IMD-")
    assert hasattr(weather, "imd_advisory")
    assert len(weather.imd_advisory) > 10


def test_imd_resilient_fallback_on_network_failure():
    """Verify fallback resilience to calibrated climate model if network calls fail."""
    _WEATHER_CACHE.clear()
    with patch("urllib.request.urlopen", side_effect=Exception("Simulated Network Outage")):
        weather = get_section_weather("KNP-PRYJ-SEC-B")
        assert weather is not None
        assert weather.section_id == "KNP-PRYJ-SEC-B"
        assert weather.imd_color_code == "GREEN"
        assert weather.imd_alert_level == "NO_WARNING"
        assert weather.imd_station_id == "IMD-42452"
        assert "IMD GREEN" in weather.imd_advisory


def test_fastapi_weather_endpoint_with_imd():
    """Verify FastAPI /api/weather/{section_id} serves IMD fields."""
    _WEATHER_CACHE.clear()
    client = TestClient(app)
    response = client.get("/api/weather/KNP-PRYJ-SEC-B")
    assert response.status_code == 200
    data = response.json()

    assert data["section_id"] == "KNP-PRYJ-SEC-B"
    assert "imd_color_code" in data
    assert data["imd_color_code"] in {"GREEN", "YELLOW", "ORANGE", "RED"}
    assert "imd_alert_level" in data
    assert "imd_station_id" in data
    assert data["imd_station_id"] == "IMD-42452"
    assert "imd_advisory" in data
