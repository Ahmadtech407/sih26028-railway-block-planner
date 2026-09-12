"""Tests for Indian Railways Station Network, Corridor Distances, and Kinematics."""

import pytest
from backend.services.station_network import (
    STATION_REGISTRY,
    find_station,
    get_route_stops,
    resolve_station_route,
)


def test_station_fuzzy_matching():
    # Codes
    assert find_station("NDLS")["code"] == "NDLS"
    assert find_station("JAT")["code"] == "JAT"
    assert find_station("CNB")["code"] == "CNB"
    assert find_station("PRYJ")["code"] == "PRYJ"

    # Common names (case-insensitive)
    assert find_station("delhi")["code"] == "NDLS"
    assert find_station("New Delhi")["code"] == "NDLS"
    assert find_station("JAMMU")["code"] == "JAT"
    assert find_station("jammu tawi")["code"] == "JAT"
    assert find_station("Kanpur")["code"] == "CNB"
    assert find_station("Prayagraj")["code"] == "PRYJ"
    assert find_station("Allahabad")["code"] == "PRYJ"
    assert find_station("Varanasi")["code"] == "BSB"
    assert find_station("Mumbai")["code"] == "MMCT"
    assert find_station("Howrah")["code"] == "HWH"


def test_delhi_jammu_corridor_resolution():
    route = resolve_station_route("DELHI", "JAMMU", speed_kmph=112.0, progress_pct=50.0)
    assert route["origin_code"] == "NDLS"
    assert route["destination_code"] == "JAT"
    assert route["total_distance_km"] == 588.0
    # At 50% of 588 km = 294.0 km
    assert route["covered_distance_km"] == 294.0
    assert route["remaining_distance_km"] == 294.0
    assert route["completion_pct"] == 50.0

    # Mathematical identity: covered + remaining == total
    assert round(route["covered_distance_km"] + route["remaining_distance_km"], 1) == route["total_distance_km"]

    # At 294 km along Delhi->Jammu (Ambala at 198 km, Ludhiana at 312 km), next stop must be Ludhiana!
    assert route["next_station_code"] == "LDH"
    assert "Ludhiana" in route["next_station_name"]
    # Distance to Ludhiana = 312 - 294 = 18.0 km
    assert route["next_station_distance_km"] == 18.0
    # ETA to Ludhiana at 112 km/h: round(18.0 / 112 * 60) = 10 min
    assert route["next_station_eta_min"] == 10

    # Destination ETA at 112 km/h: round(294 / 112 * 60) = 158 min
    assert route["destination_eta_min"] == 158

    # Target weather coordinates must be Ludhiana (or Jammu corridor)
    lat, lon, name = route["weather_coords"]
    assert 30.0 < lat < 33.0
    assert "LDH" in name or "Ludhiana" in name


def test_kanpur_prayagraj_corridor_resolution():
    route = resolve_station_route("KANPUR", "PRAYAGRAJ", speed_kmph=110.0, progress_pct=50.0)
    assert route["origin_code"] == "CNB"
    assert route["destination_code"] == "PRYJ"
    assert route["total_distance_km"] == 194.0
    assert route["covered_distance_km"] == 97.0
    assert route["remaining_distance_km"] == 97.0
    assert route["next_station_code"] == "SRO"  # Sirathu at 130 km
    assert route["next_station_distance_km"] == 33.0  # 130 - 97 = 33 km


def test_reverse_corridor_inverts_distances():
    route = resolve_station_route("JAMMU", "DELHI", speed_kmph=112.0, progress_pct=20.0)
    assert route["origin_code"] == "JAT"
    assert route["destination_code"] == "NDLS"
    assert route["total_distance_km"] == 588.0
    assert route["covered_distance_km"] == 117.6
    # 20% along Jammu -> Delhi (Pathankot is at 108 km from Jammu): next stop is Jalandhar Cantt (218 km from Jammu)
    assert route["next_station_distance_km"] > 0
