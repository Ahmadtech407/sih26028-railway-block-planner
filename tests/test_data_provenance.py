"""
Unit & Integration Tests for RailTrack Data Provenance Architecture.
Validates:
1. Provenanced record envelope structure, required fields, and ISO timestamps.
2. Freshness thresholds configuration.
3. Train kinematics validation and physical bounds enforcement (speed <= 165 km/h, GPS boundaries).
4. Meteorological parameter validation and plausibility intervals.
5. Strict 10-digit numeric PNR format validation.
6. Fail-fast Circuit Breaker lifecycle, tripping, and auto-cooling reset.
7. Truthful provenance badge HTML rendering across all operational classifications.
8. Truthful user-facing status label formatting adhering to Phase 3 standards.
"""

import time
from datetime import datetime

from backend.services.data_provenance import (
    SourceType,
    DataStatus,
    FRESHNESS_THRESHOLDS,
    create_provenanced_record,
    validate_train_kinematics,
    validate_weather_parameters,
    validate_pnr_format,
    CircuitBreaker,
)
from ui.components.provenance import (
    get_provenance_badge_html,
    format_truthful_provenance_label,
)


def test_create_provenanced_record_schema():
    """Verify provenanced record contains all mandatory traceability fields."""
    rec = create_provenanced_record(
        data={"train_number": "22436", "speed": 112.0},
        source_name="CRIS_TMS",
        source_type=SourceType.OFFICIAL,
        status=DataStatus.LIVE,
        source_timestamp="2026-10-11T12:00:00+00:00",
        limitations="Restricted to Northern Railway monitored sections",
    )

    assert rec["source_name"] == "CRIS_TMS"
    assert rec["source_type"] == "official"
    assert rec["status"] == "live"
    assert rec["is_stale"] is False
    assert rec["source_timestamp"] == "2026-10-11T12:00:00+00:00"
    assert "limitations" in rec
    assert rec["request_id"] is not None
    # Validate ISO datetime format
    assert datetime.fromisoformat(rec["fetched_at"].replace("Z", "+00:00"))


def test_freshness_thresholds_defined():
    """Verify standard freshness thresholds for all railway data types."""
    assert FRESHNESS_THRESHOLDS["live_gps"] == 120
    assert FRESHNESS_THRESHOLDS["live_telemetry"] == 180
    assert FRESHNESS_THRESHOLDS["weather"] == 900
    assert FRESHNESS_THRESHOLDS["predictions"] == 300
    assert FRESHNESS_THRESHOLDS["timetables"] == 86400


def test_validate_train_kinematics_valid():
    """Verify clean pass for authentic train running parameters."""
    valid_train = {
        "train_number": "22436",
        "speed_kmph": 112.0,
        "position_km": 414.2,
        "gps_lat": 26.4539,
        "gps_lon": 80.3508,
    }
    is_valid, errors = validate_train_kinematics(valid_train)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_train_kinematics_detects_violations():
    """Verify physical impossibility and out-of-bounds kinematic detection."""
    # 1. Negative speed
    ok, errs = validate_train_kinematics({"speed_kmph": -15.0})
    assert ok is False
    assert any("Negative speed" in e for e in errs)

    # 2. Implausible overspeed (> 165 km/h)
    ok, errs = validate_train_kinematics({"speed_kmph": 210.0})
    assert ok is False
    assert any("Implausible speed" in e for e in errs)

    # 3. Out of bounds GPS (e.g. coordinates in Europe or Atlantic)
    ok, errs = validate_train_kinematics({"gps_lat": 51.5074, "gps_lon": -0.1278})
    assert ok is False
    assert any("outside Indian railway network" in e for e in errs)

    # 4. Negative position
    ok, errs = validate_train_kinematics({"position_km": -4.5})
    assert ok is False
    assert any("Negative track position" in e for e in errs)


def test_validate_weather_parameters_valid():
    """Verify authentic meteorological parameter intervals."""
    weather = {
        "temperature_c": 28.5,
        "humidity_pct": 65.0,
        "wind_speed_kmph": 14.0,
        "visibility_km": 8.5,
    }
    is_valid, errors = validate_weather_parameters(weather)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_weather_parameters_detects_outliers():
    """Verify out-of-bound meteorological values are flagged."""
    # Temperature out of bounds
    ok, errs = validate_weather_parameters({"temperature_c": 75.0})
    assert ok is False
    assert any("Temperature" in e for e in errs)

    # Humidity > 100%
    ok, errs = validate_weather_parameters({"humidity_pct": 115.0})
    assert ok is False
    assert any("Humidity" in e for e in errs)

    # Wind speed > 200 km/h
    ok, errs = validate_weather_parameters({"wind_speed_kmph": 250.0})
    assert ok is False
    assert any("Wind speed" in e for e in errs)


def test_validate_pnr_format():
    """Verify strict 10-digit numeric PNR validation."""
    assert validate_pnr_format("8429103847") is True
    assert validate_pnr_format("1234567890") is True
    # Length violations
    assert validate_pnr_format("123456789") is False
    assert validate_pnr_format("12345678901") is False
    # Alphanumeric violations
    assert validate_pnr_format("84291A3847") is False
    assert validate_pnr_format("PNR8429103") is False
    assert validate_pnr_format("") is False
    assert validate_pnr_format(None) is False


def test_circuit_breaker_lifecycle():
    """Verify Circuit Breaker trips after threshold and resets after cooling period."""
    cb = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=0.1)
    assert cb.can_execute() is True

    # 1st failure
    cb.record_failure()
    assert cb.can_execute() is True

    # 2nd failure trips the circuit
    cb.record_failure()
    assert cb.is_open is True
    assert cb.can_execute() is False

    # Wait for cooling timeout
    time.sleep(0.12)
    assert cb.can_execute() is True

    # Success closes the breaker completely
    cb.record_success()
    assert cb.is_open is False
    assert cb.failure_count == 0


def test_provenance_badge_html_all_variants():
    """Verify all provenance badge HTML classifications render valid markup."""
    statuses = ["VERIFIED LIVE", "SCHEDULED", "PREDICTED", "AI ADVISORY", "DEMO DATA", "UNAVAILABLE", "STALE"]
    for st in statuses:
        html_badge = get_provenance_badge_html(st, source="SYSTEM_SOURCE", is_stale=(st == "STALE"))
        assert "rt-badge" in html_badge
        assert st in html_badge or "STALE" in html_badge


def test_truthful_provenance_labels():
    """Verify user-facing truth-in-data status strings strictly match Phase 3 standards."""
    assert "LIVE — Source verified" in format_truthful_provenance_label("LIVE", source_name="GPS", age_seconds=45)
    assert "PREDICTED — Model estimate — Not an official ETA" == format_truthful_provenance_label("PREDICTED")
    assert "CACHED — Last updated" in format_truthful_provenance_label("CACHED", age_seconds=1200)
    assert "SCHEDULED — Timetable information, not live tracking" == format_truthful_provenance_label("SCHEDULED")
    assert "DEMO — Simulated data; not for operational decisions" == format_truthful_provenance_label("DEMO")
    assert "UNAVAILABLE — Live source did not respond" == format_truthful_provenance_label("UNAVAILABLE")
