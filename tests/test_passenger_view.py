"""Focused tests for passenger-facing presentation logic."""

from passenger_app import (
    destination_eta_minutes,
    delay_minutes,
    distance_to_next_station,
    get_route_stations,
    is_platform_change,
    platform_source_label,
    selected_train,
    source_label,
)


def test_passenger_source_labels_are_explicit():
    assert source_label("LIVE_GPS") == "LIVE GPS DATA"
    assert source_label("SIMULATED") == "SIMULATED DEMO DATA"
    assert source_label("UNAVAILABLE") == "DATA SOURCE UNAVAILABLE"
    assert platform_source_label("MOCK_RAILWAY_FEED") == "DEMO PLATFORM DATA"
    assert platform_source_label("CRIS_TMS") == "LIVE PLATFORM DATA"


def test_passenger_train_search_matches_number_or_name():
    trains = [{"train_number": "22436", "name": "Vande Bharat Express"}]
    assert selected_train(trains, "22436")["name"] == "Vande Bharat Express"
    assert selected_train(trains, "vande")["train_number"] == "22436"
    assert selected_train(trains, "unknown") is None


def test_passenger_route_distance_supports_both_directions():
    section = {"start_km": 400.0, "end_km": 442.5}
    assert distance_to_next_station({"position_km": 420, "direction": "UP"}, section) == 22.5
    assert distance_to_next_station({"position_km": 420, "direction": "DOWN"}, section) == 20.0


def test_passenger_platform_change_alert_is_data_driven():
    assert is_platform_change({"platform_status": "PLATFORM_CHANGED"})
    assert is_platform_change({"platform_status": "REASSIGNED"})
    assert not is_platform_change({"platform_status": "ASSIGNED"})


def test_passenger_delay_value_supports_delayed_status():
    assert delay_minutes({"delay_minutes": 18, "status": "DELAYED"}) == 18
    assert delay_minutes({"status": "ON TIME"}) == 0


def test_passenger_destination_eta_uses_position_and_speed():
    assert destination_eta_minutes({"position_km": 420, "speed_kmph": 100, "direction": "UP"}, {"start_km": 400, "end_km": 442.5}) == 14
    assert destination_eta_minutes({"position_km": 420, "speed_kmph": 0, "direction": "UP"}, {"start_km": 400, "end_km": 442.5}) is None


def test_get_route_stations_resolves_delhi_jammu_corridor():
    train = {"passenger_from": "New Delhi", "passenger_to": "Jammu Tawi"}
    section = {"section_id": "NDLS-JAT", "length_km": 588.0}
    stations = get_route_stations(section, train)
    assert len(stations) >= 2
    assert stations[0]["name"] == "New Delhi"
    assert stations[-1]["name"] == "Jammu Tawi"
    assert any(s["name"] == "Ludhiana Junction" for s in stations)
    assert all("lat" in s and "lon" in s for s in stations)


def test_get_route_stations_resolves_kanpur_prayagraj_corridor():
    train = {"passenger_from": "Kanpur Central", "passenger_to": "Prayagraj Junction"}
    section = {"section_id": "CNB-PRYJ", "length_km": 194.0}
    stations = get_route_stations(section, train)
    assert len(stations) >= 2
    assert stations[0]["name"] == "Kanpur Central"
    assert stations[-1]["name"] == "Prayagraj Junction"
    assert all("lat" in s and "lon" in s for s in stations)
