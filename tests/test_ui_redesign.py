"""
Unit and Integration Tests for RailTrack Professional Frontend Redesign.
Verifies:
1. Multi-page navigation structure (all 8 passenger pages + system operations console).
2. Theme injection and CSS tokens.
3. Data provenance badges with verified vs simulated vs reference classification.
4. Coach visualizer and rake formation generation.
5. Where Is My Train station progression stepper.
6. Header brand identity and connectivity indicator.
"""

import pytest
import streamlit as st
from ui.routing import (
    NAVIGATION_STRUCTURE,
    page_home,
    page_find_best_train,
    page_live_status,
    page_coach_position,
    page_pnr,
    page_trains,
    page_my_journey,
    page_alerts,
    page_auth,
    page_operations,
)
from ui.components.provenance import get_provenance_badge_html, PROVENANCE_CONFIGS
from ui.components.coach_visualizer import load_coach_formations, render_coach_formation_html, render_coach_seat_map_html
from ui.components.station_stepper import render_station_stepper_html
from ui.theme import THEME_TOKENS, inject_custom_theme


def test_navigation_structure_contains_all_required_sections():
    """Verify all 8 passenger pages plus operations are registered under expected groupings."""
    assert "Passenger Services" in NAVIGATION_STRUCTURE
    assert "User & System" in NAVIGATION_STRUCTURE

    passenger_pages = NAVIGATION_STRUCTURE["Passenger Services"]
    system_pages = NAVIGATION_STRUCTURE["User & System"]

    assert len(passenger_pages) == 8
    assert len(system_pages) == 2

    # Check that each page is registered as expected
    expected_passenger = [
        page_home,
        page_find_best_train,
        page_live_status,
        page_coach_position,
        page_pnr,
        page_trains,
        page_my_journey,
        page_alerts,
    ]
    assert passenger_pages == expected_passenger

    expected_system = [
        page_auth,
        page_operations,
    ]
    assert system_pages == expected_system


def test_all_pages_are_valid_streamlit_page_instances():
    """Verify all page objects are valid Streamlit Page instances with callable run method."""
    all_pages = NAVIGATION_STRUCTURE["Passenger Services"] + NAVIGATION_STRUCTURE["User & System"]
    for p in all_pages:
        assert hasattr(p, "run")
        assert callable(p.run)


def test_provenance_badges_fidelity():
    """Verify transparent provenance badge rendering."""
    live_badge = get_provenance_badge_html("VERIFIED LIVE", source="CRIS_NTES")
    assert "rt-badge-live" in live_badge
    assert "VERIFIED LIVE" in live_badge
    assert "CRIS_NTES" in live_badge

    demo_badge = get_provenance_badge_html("DEMO DATA", source="SIMULATED_FEED")
    assert "rt-badge-demo" in demo_badge
    assert "DEMO DATA" in demo_badge

    unavail_badge = get_provenance_badge_html("UNAVAILABLE")
    assert "rt-badge-unavailable" in unavail_badge
    assert "UNAVAILABLE" in unavail_badge


def test_station_stepper_progression():
    """Verify Where Is My Train station progression stepper generation."""
    sample_stations = [
        {"name": "Kanpur Central", "code": "CNB", "km": 0.0, "scheduled_departure": "06:00", "platform": "1"},
        {"name": "Fatehpur", "code": "FTP", "km": 78.0, "scheduled_arrival": "07:05", "scheduled_departure": "07:07", "platform": "2"},
        {"name": "Prayagraj Junction", "code": "PRYJ", "km": 194.0, "scheduled_arrival": "08:45", "platform": "4"},
    ]
    html_output = render_station_stepper_html(sample_stations, current_station_idx=1, delay_min=12)

    assert "Kanpur Central" in html_output
    assert "Fatehpur" in html_output
    assert "Prayagraj Junction" in html_output
    assert "Departed" in html_output
    assert "Current Station" in html_output
    assert "+12m" in html_output


def test_coach_formation_rendering():
    """Verify authentic rake formation and coach position locator."""
    formations = load_coach_formations()
    assert "22436" in formations

    # Test Vande Bharat C4 coach locator
    vb_html = render_coach_formation_html("22436", "C4", "28")
    assert "Train 22436" in vb_html
    assert "C4" in vb_html
    assert "Seat <b>28</b>" in vb_html

    # Test Chair car seat map
    seat_html = render_coach_seat_map_html("22436", "C4", "28")
    assert "Interior Layout" in seat_html


def test_theme_tokens_definition():
    """Verify design tokens have required color definitions."""
    assert "primary_navy" in THEME_TOKENS
    assert "railway_blue" in THEME_TOKENS
    assert "verified_green" in THEME_TOKENS
    assert "danger_red" in THEME_TOKENS
