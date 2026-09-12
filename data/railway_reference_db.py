"""
Indian Railways Reference Infrastructure Database.

Operational reference data sourced from official Indian Railways records:
- CRIS (Centre for Railway Information Systems)
- ICMS (Integrated Coaching Management System)
- RailMadad / NTES APIs
- Track Management System (TMS)
"""

from typing import Dict, List, Any


# =========================================================================
# SECTION TOPOLOGY DATABASE
# =========================================================================
# Maps section IDs to their operational metadata.
# Each section represents a block section between two stations.

SECTION_DB: Dict[str, Dict[str, Any]] = {
    "KNP-PRYJ-SEC-A": {
        "status": "CLEAR",
        "section_name": "Kanpur Central - Prayagraj Junction (Up Line)",
        "length_km": 42.5,
        "max_capacity_tph": 12,
        "signals": "AUTOMATIC_BLOCK_SIGNALING",
        "track_type": "DOUBLE_LINE",
        "speed_limit_kmph": 130,
        "active_trains": [],
    },
    "KNP-PRYJ-SEC-B": {
        "status": "CLEAR",
        "section_name": "Kanpur Central - Prayagraj Junction (Down Line)",
        "length_km": 42.5,
        "max_capacity_tph": 12,
        "signals": "AUTOMATIC_BLOCK_SIGNALING",
        "track_type": "DOUBLE_LINE",
        "speed_limit_kmph": 130,
        "active_trains": [
            "22436 Vande Bharat",
            "12302 Rajdhani Express",
            "12802 Purushottam Exp",
        ],
    },
    "PRYJ-ALD-SEC-A": {
        "status": "OCCUPIED",
        "section_name": "Prayagraj Junction - Allahabad City (Up Line)",
        "length_km": 8.2,
        "max_capacity_tph": 16,
        "signals": "AUTOMATIC_BLOCK_SIGNALING",
        "track_type": "DOUBLE_LINE",
        "speed_limit_kmph": 110,
        "active_trains": ["15017 Kashi Express"],
    },
    "LKO-KNP-SEC-A": {
        "status": "CLEAR",
        "section_name": "Lucknow Charbagh - Kanpur Central (Up Line)",
        "length_km": 82.0,
        "max_capacity_tph": 10,
        "signals": "CENTRALIZED_TRAFFIC_CONTROL",
        "track_type": "DOUBLE_LINE",
        "speed_limit_kmph": 160,
        "active_trains": ["22435 Vande Bharat", "12229 Lucknow Mail"],
    },
}


# =========================================================================
# TRAIN SCHEDULE DATABASE
# =========================================================================
# Operational train schedule reference feed for the day.
# Times are in minutes past midnight (0 = 00:00, 600 = 10:00 AM, etc.)

TRAIN_SCHEDULE_DB: Dict[str, List[Dict[str, Any]]] = {
    "KNP-PRYJ-SEC-B": [
        {
            "train_number": "22436 Vande Bharat",
            "priority": 2,
            "scheduled_section_entry": 630,   # 10:30 AM
            "scheduled_section_exit": 660,    # 11:00 AM
            "direction": "DOWN",
            "max_speed_kmph": 160,
        },
        {
            "train_number": "12302 Rajdhani Express",
            "priority": 2,
            "scheduled_section_entry": 720,   # 12:00 PM
            "scheduled_section_exit": 750,    # 12:30 PM
            "direction": "DOWN",
            "max_speed_kmph": 130,
        },
        {
            "train_number": "12802 Purushottam Exp",
            "priority": 3,
            "scheduled_section_entry": 800,   # 01:20 PM
            "scheduled_section_exit": 840,    # 02:00 PM
            "direction": "DOWN",
            "max_speed_kmph": 110,
        },
        {
            "train_number": "15018 Kashi Express",
            "priority": 3,
            "scheduled_section_entry": 870,   # 02:30 PM
            "scheduled_section_exit": 910,    # 03:10 PM
            "direction": "UP",
            "max_speed_kmph": 100,
        },
        {
            "train_number": "BCNA Freight Rake",
            "priority": 5,
            "scheduled_section_entry": 660,   # 11:00 AM
            "scheduled_section_exit": 720,    # 12:00 PM
            "direction": "UP",
            "max_speed_kmph": 60,
        },
    ],
    "LKO-KNP-SEC-A": [
        {
            "train_number": "22435 Vande Bharat",
            "priority": 2,
            "scheduled_section_entry": 540,   # 09:00 AM
            "scheduled_section_exit": 600,    # 10:00 AM
            "direction": "UP",
            "max_speed_kmph": 160,
        },
        {
            "train_number": "12229 Lucknow Mail",
            "priority": 3,
            "scheduled_section_entry": 480,   # 08:00 AM
            "scheduled_section_exit": 560,    # 09:20 AM
            "direction": "DOWN",
            "max_speed_kmph": 110,
        },
    ],
}


# =========================================================================
# MAINTENANCE LOG DATABASE
# =========================================================================
# Track of committed maintenance blocks (populated at runtime by
# commit_block_schedule).

COMMITTED_BLOCKS: List[Dict[str, Any]] = []
