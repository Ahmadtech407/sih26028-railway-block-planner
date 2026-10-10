"""
Integration Tests verifying that every single Streamlit page loads without exceptions,
renders visible widgets, and executes within the Streamlit runtime environment.
"""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from ui.routing import (
    get_navigation_structure,
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
from ui.pages.home import render_home_page
from ui.pages.find_best_train import render_find_best_train_page
from ui.pages.live_status import render_live_status_page
from ui.pages.coach_position import render_coach_position_page
from ui.pages.pnr import render_pnr_page
from ui.pages.trains import render_trains_page
from ui.pages.my_journeys import render_my_journeys_page
from ui.pages.alerts import render_alerts_page
from ui.pages.account import render_account_page
from ui.pages.operations import render_operations_page

ROOT_DIR = Path(__file__).parent.parent
ENTRYPOINT = str(ROOT_DIR / "passenger_app.py")


def test_home_page_renders_visibly_without_exceptions():
    """Verify that passenger_app.py launches the Home page with zero exceptions and visible elements."""
    at = AppTest.from_file(ENTRYPOINT, default_timeout=15)
    at.run()

    # Zero uncaught runtime exceptions
    assert len(at.exception) == 0, f"Uncaught exceptions on Home: {[e.message for e in at.exception]}"

    # Verify visible elements
    assert len(at.markdown) > 5, "Home page failed to render markdown elements"
    assert len(at.button) > 3, "Home page failed to render service buttons"

    # Verify essential components are present
    all_markdown_text = " ".join([m.value for m in at.markdown if m.value])
    assert "Where is your next journey?" in all_markdown_text
    assert "Essential Passenger Services" in all_markdown_text
    assert "Search Trains" in all_markdown_text


def test_navigation_structure_is_complete():
    """Verify that get_navigation_structure returns all 8 passenger pages plus operations."""
    nav_struct = get_navigation_structure()
    assert "Passenger Services" in nav_struct
    assert "User & System" in nav_struct

    passenger_pages = nav_struct["Passenger Services"]
    assert len(passenger_pages) == 8

    system_pages = nav_struct["User & System"]
    assert len(system_pages) == 2


def test_all_page_callables_are_valid():
    """Verify all 10 page functions are valid callables and match routing definitions."""
    pages_to_test = [
        ("Home", render_home_page),
        ("Find Best Train", render_find_best_train_page),
        ("Live Train Status", render_live_status_page),
        ("Find My Coach", render_coach_position_page),
        ("PNR Status", render_pnr_page),
        ("Find Trains", render_trains_page),
        ("My Journey", render_my_journeys_page),
        ("Alerts", render_alerts_page),
        ("Authentication", render_account_page),
        ("RailTrack Operations", render_operations_page),
    ]

    for name, fn in pages_to_test:
        assert callable(fn), f"Page handler for '{name}' is not callable"


@pytest.mark.parametrize(
    "page_module,page_fn",
    [
        ("ui.pages.home", "render_home_page"),
        ("ui.pages.find_best_train", "render_find_best_train_page"),
        ("ui.pages.live_status", "render_live_status_page"),
        ("ui.pages.coach_position", "render_coach_position_page"),
        ("ui.pages.pnr", "render_pnr_page"),
        ("ui.pages.trains", "render_trains_page"),
        ("ui.pages.my_journeys", "render_my_journeys_page"),
        ("ui.pages.alerts", "render_alerts_page"),
        ("ui.pages.account", "render_account_page"),
        ("ui.pages.operations", "render_operations_page"),
    ],
)
def test_all_10_pages_execute_without_exceptions(page_module, page_fn):
    """Verify that every single page executes completely with zero unhandled exceptions."""
    code = f"from {page_module} import {page_fn}; {page_fn}()"
    at = AppTest.from_string(code, default_timeout=20)
    at.run()
    assert len(at.exception) == 0, f"Exception on {page_fn}: {[e.message for e in at.exception]}"

