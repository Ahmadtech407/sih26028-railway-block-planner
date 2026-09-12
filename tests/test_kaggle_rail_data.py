"""Tests for Pre-Cleaned Kaggle Indian Railways Dataset & Corridor Kinematics."""

import pytest
from backend.data.kaggle_rail_dataset import (
    KAGGLE_STATION_REGISTRY,
    KAGGLE_CORRIDORS,
    KAGGLE_ALIASES,
    get_empirical_delay_estimate,
)
from backend.services.station_network import (
    STATION_REGISTRY,
    find_station,
    resolve_station_route,
)


def test_kaggle_station_registry_coverage():
    """Verify pre-cleaned Kaggle dataset includes nationwide stations across all 18 zones."""
    assert len(KAGGLE_STATION_REGISTRY) >= 80
    assert len(STATION_REGISTRY) >= 80

    # Test key regional junction hubs
    assert "PUNE" in STATION_REGISTRY
    assert "BZA" in STATION_REGISTRY  # Vijayawada
    assert "NGP" in STATION_REGISTRY  # Nagpur
    assert "VGLB" in STATION_REGISTRY  # Jhansi
    assert "MTJ" in STATION_REGISTRY  # Mathura
    assert "UBL" in STATION_REGISTRY  # Hubballi
    assert "CBE" in STATION_REGISTRY  # Coimbatore
    assert "TATA" in STATION_REGISTRY  # Tatanagar

    # Check station metadata fidelity
    pune = STATION_REGISTRY["PUNE"]
    assert pune["zone"] == "CR"
    assert 18.4 < pune["lat"] < 18.6
    assert 73.7 < pune["lon"] < 74.0


def test_kaggle_fuzzy_aliases():
    """Verify colloquial city aliases resolve accurately to official station codes."""
    assert find_station("pune")["code"] == "PUNE"
    assert find_station("vizag")["code"] == "VSKP"
    assert find_station("bangalore")["code"] == "SBC"
    assert find_station("tatanagar")["code"] == "TATA"
    assert find_station("shirdi")["code"] == "SNSI"
    assert find_station("madras")["code"] == "MAS"
    assert find_station("calicut")["code"] == "CLT"


def test_mumbai_pune_corridor_resolution():
    """Verify CSMT to PUNE corridor resolution using official Kaggle track chainage."""
    route = resolve_station_route("CSMT", "PUNE", speed_kmph=80.0, progress_pct=50.0)
    assert route["origin_code"] == "CSMT"
    assert route["destination_code"] == "PUNE"
    assert route["total_distance_km"] == 192.0
    assert route["covered_distance_km"] == 96.0
    assert route["remaining_distance_km"] == 96.0

    # At 96 km (Thane at 34, Kalyan at 54, Karjat at 100): next stop should be Karjat!
    assert route["next_station_code"] == "KJT"
    assert route["next_station_distance_km"] == 4.0

    # Historical delay profile is returned
    assert "historical_delay_profile" in route
    assert "expected_delay_min" in route["historical_delay_profile"]


def test_delhi_chennai_grand_trunk_corridor():
    """Verify NDLS to MAS Southern trunk corridor resolution."""
    route = resolve_station_route("DELHI", "CHENNAI", speed_kmph=110.0, progress_pct=10.0)
    assert route["origin_code"] == "NDLS"
    assert route["destination_code"] == "MAS"
    assert route["total_distance_km"] == 2182.0
    assert route["covered_distance_km"] == 218.2
    assert route["intermediate_stops"][1]["code"] == "MTJ"
    assert route["intermediate_stops"][-1]["code"] == "MAS"


def test_empirical_delay_estimate_by_zone():
    """Verify Northern fog-prone zones show higher expected delays than Southern zones."""
    nr_delay = get_empirical_delay_estimate("NR", is_winter=True, priority_tier=2)
    sr_delay = get_empirical_delay_estimate("SR", is_winter=True, priority_tier=2)

    assert nr_delay["expected_delay_min"] > sr_delay["expected_delay_min"]
    assert nr_delay["junction_choke_prob"] > sr_delay["junction_choke_prob"]
