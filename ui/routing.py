"""
RailTrack Navigation & Page Routing Configuration.
Defines all st.Page controllers and hierarchy for st.navigation across the
8 dedicated passenger pages and administrative operations console.
Guarantees self-healing page initialization under Streamlit runtime contexts.
"""

from typing import Dict, List, Any
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from ui.pages.home import render_home_page
from ui.pages.find_best_train import render_find_best_train_page
from ui.pages.live_status import render_live_status_page
from ui.pages.coach_position import render_coach_position_page
from ui.pages.pnr import render_pnr_page
from ui.pages.account import render_account_page
from ui.pages.alerts import render_alerts_page
from ui.pages.my_journeys import render_my_journeys_page
from ui.pages.trains import render_trains_page
from ui.pages.operations import render_operations_page


# Global placeholders
page_home = None
page_find_best_train = None
page_live_status = None
page_coach_position = None
page_pnr = None
page_trains = None
page_my_journey = None
page_alerts = None
page_auth = None
page_account = None
page_my_journeys = None
page_operations = None
NAVIGATION_STRUCTURE = {}


def init_routing() -> Dict[str, List[Any]]:
    """Initialize or re-initialize Page instances when a Streamlit context is available."""
    global page_home, page_find_best_train, page_live_status, page_coach_position
    global page_pnr, page_trains, page_my_journey, page_alerts, page_auth, page_account, page_my_journeys, page_operations
    global NAVIGATION_STRUCTURE

    # Persistent Page instances matching the 8 primary required passenger routes
    page_home = st.Page(render_home_page, title="Home", icon="🏠", default=True)
    page_find_best_train = st.Page(render_find_best_train_page, title="Find Best Train", icon="🤖", url_path="find-best-train")
    page_live_status = st.Page(render_live_status_page, title="Live Train Status", icon="📍", url_path="live-status")
    page_coach_position = st.Page(render_coach_position_page, title="Find My Coach", icon="💺", url_path="find-my-coach")
    page_pnr = st.Page(render_pnr_page, title="PNR Status", icon="🎫", url_path="pnr")
    page_trains = st.Page(render_trains_page, title="Find Trains", icon="🔍", url_path="trains")
    page_my_journey = st.Page(render_my_journeys_page, title="My Journey", icon="🧳", url_path="my-journey")
    page_alerts = st.Page(render_alerts_page, title="Alerts", icon="🔔", url_path="alerts")

    # User & System pages
    page_auth = st.Page(render_account_page, title="Authentication", icon="🔐", url_path="auth")
    page_account = page_auth  # backward-compatibility alias
    page_my_journeys = page_my_journey  # backward-compatibility alias
    page_operations = st.Page(render_operations_page, title="RailTrack Operations", icon="🛠️", url_path="operations")

    NAVIGATION_STRUCTURE = {
        "Passenger Services": [
            page_home,
            page_find_best_train,
            page_live_status,
            page_coach_position,
            page_pnr,
            page_trains,
            page_my_journey,
            page_alerts,
        ],
        "User & System": [
            page_auth,
            page_operations,
        ],
    }
    return NAVIGATION_STRUCTURE


# Initial call at import
init_routing()


def get_navigation_structure() -> Dict[str, List[Any]]:
    """Return navigation structure, ensuring pages are initialized under active runtime context."""
    if get_script_run_ctx() is not None:
        if page_home is None or not hasattr(page_home, "_page") or page_home._page is None:
            init_routing()
    return NAVIGATION_STRUCTURE
