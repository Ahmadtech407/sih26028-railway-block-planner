"""
RailTrack Navigation & Page Routing Configuration.
Defines all st.Page controllers and hierarchy for st.navigation across the
8 dedicated passenger pages and administrative operations console.
"""

import streamlit as st
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


# Persistent Page instances matching the 8 primary required passenger routes
page_home = st.Page(render_home_page, title="Home", icon="🏠", url_path="")
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
