"""
Ticket Verification Service for Indian Railways Passenger App (SIH26028).

Validates IRCTC PNRs, electronic reservation slips (ERS), QR code payloads,
and barcode data against railway passenger manifests.
"""

from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, Optional


# Pre-seeded IRCTC passenger records for electronic reservation verification (PRS/ERS)
KNOWN_TICKETS: Dict[str, Dict[str, Any]] = {
    "8410000477": {
        "pnr": "8410000477",
        "ticket_id": "IRCTC-22436-841000",
        "passenger": {
            "name": "John Doe",
            "age": 28,
            "gender": "Male",
            "berth_preference": "Window (W)",
        },
        "journey": {
            "train_number": "22436",
            "train_name": "Vande Bharat Express",
            "from_station": "New Delhi (NDLS)",
            "to_station": "Jammu Tawi (JAT)",
            "departure_time": "06:00 AM",
            "arrival_time": "02:00 PM",
            "travel_date": "05 Sep 2026",
            "class_code": "CC",
            "class_name": "AC Chair Car",
            "quota": "General (GN)",
        },
        "booking": {
            "status": "CNF",
            "status_detail": "Confirmed / Allotted",
            "coach": "C6",
            "seat_number": "46",
            "berth_type": "Window",
            "fare": 1480.00,
            "chart_status": "CHART PREPARED",
            "platform_expected": "PF 1",
        },
    },
    "8429103847": {
        "pnr": "8429103847",
        "ticket_id": "IRCTC-22436-842910",
        "passenger": {
            "name": "John Doe",
            "age": 28,
            "gender": "Male",
            "berth_preference": "Window (W)",
        },
        "journey": {
            "train_number": "22436",
            "train_name": "Vande Bharat Express",
            "from_station": "New Delhi (NDLS)",
            "to_station": "Jammu Tawi (JAT)",
            "departure_time": "06:00 AM",
            "arrival_time": "02:00 PM",
            "travel_date": "05 Sep 2026",
            "class_code": "CC",
            "class_name": "AC Chair Car",
            "quota": "General (GN)",
        },
        "booking": {
            "status": "CNF",
            "status_detail": "Confirmed / Allotted",
            "coach": "C6",
            "seat_number": "46",
            "berth_type": "Window",
            "fare": 1480.00,
            "chart_status": "CHART PREPARED",
            "platform_expected": "PF 1",
        },
    },
    "2840192841": {
        "pnr": "2840192841",
        "ticket_id": "IRCTC-12302-284019",
        "passenger": {
            "name": "Priya Sharma",
            "age": 31,
            "gender": "Female",
            "berth_preference": "Side Lower (SL)",
        },
        "journey": {
            "train_number": "12302",
            "train_name": "Howrah Rajdhani Express",
            "from_station": "New Delhi (NDLS)",
            "to_station": "Howrah Jn (HWH)",
            "departure_time": "04:50 PM",
            "arrival_time": "09:55 AM (Next Day)",
            "travel_date": "05 Sep 2026",
            "class_code": "3A",
            "class_name": "AC 3-Tier",
            "quota": "General (GN)",
        },
        "booking": {
            "status": "CNF",
            "status_detail": "Confirmed / Allotted",
            "coach": "B2",
            "seat_number": "19",
            "berth_type": "Side Lower",
            "fare": 2345.00,
            "chart_status": "CHART PREPARED",
            "platform_expected": "PF 4",
        },
    },
    "9812401823": {
        "pnr": "9812401823",
        "ticket_id": "IRCTC-12802-981240",
        "passenger": {
            "name": "Amit Patel",
            "age": 35,
            "gender": "Male",
            "berth_preference": "Lower (L)",
        },
        "journey": {
            "train_number": "12802",
            "train_name": "Purushottam Express",
            "from_station": "New Delhi (NDLS)",
            "to_station": "Puri (PURI)",
            "departure_time": "10:40 PM",
            "arrival_time": "05:25 AM (+2 Days)",
            "travel_date": "05 Sep 2026",
            "class_code": "SL",
            "class_name": "Sleeper Class",
            "quota": "Tatkal (CK)",
        },
        "booking": {
            "status": "CNF",
            "status_detail": "Confirmed / Allotted",
            "coach": "S3",
            "seat_number": "42",
            "berth_type": "Middle Berth",
            "fare": 820.00,
            "chart_status": "CHART PREPARED",
            "platform_expected": "PF 7",
        },
    },
    "1234567890": {
        "pnr": "1234567890",
        "ticket_id": "IRCTC-12802-123456",
        "passenger": {
            "name": "Rajesh Kumar",
            "age": 32,
            "gender": "Male",
            "berth_preference": "Window (W)",
        },
        "journey": {
            "train_number": "12802",
            "train_name": "Purushottam Express",
            "from_station": "New Delhi (NDLS)",
            "to_station": "Puri (PURI)",
            "departure_time": "10:40 PM",
            "arrival_time": "05:25 AM (+2 Days)",
            "travel_date": "05 Sep 2026",
            "class_code": "2S",
            "class_name": "Second Sitting (GS)",
            "quota": "General (GN)",
        },
        "booking": {
            "status": "CNF",
            "status_detail": "Confirmed / Allotted",
            "coach": "GS1",
            "seat_number": "36",
            "berth_type": "Window",
            "fare": 345.00,
            "chart_status": "CHART PREPARED",
            "platform_expected": "PF 7",
        },
    },
}


def sanitize_payload(raw: str) -> str:
    """Strip extraneous headers, prefixes, or whitespace from scanned strings."""
    raw = str(raw).strip()
    # Support IRCTC JSON QR code payload: {"pnr":"8429103847", ...}
    if raw.startswith("{") and raw.endswith("}"):
        try:
            data = json.loads(raw)
            if "pnr" in data:
                return str(data["pnr"]).strip()
            if "ticket_id" in data:
                return str(data["ticket_id"]).strip()
        except Exception:
            pass

    # Extract 10-digit PNR if present
    match = re.search(r"\b\d{10}\b", raw)
    if match:
        return match.group(0)

    # Strip prefixes like PNR- or TKT-
    cleaned = re.sub(r"^(pnr|tkt|ticket)[\s:\-_]*", "", raw, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else raw


def verify_pnr(pnr: str) -> Optional[Dict[str, Any]]:
    """
    Canonical PNR verification provider for both Quick PNR Lookup and Find My Coach.
    Validates 10-digit PNR against database and known demo manifest.
    Returns canonical dictionary with:
    - passenger_name
    - pnr
    - train_number
    - train_name
    - coach
    - seat_number
    - berth_type
    - class_code
    - class_name
    - travel_date
    - from_station
    - to_station
    - status
    - verification_status: 'DEMO'
    - match_verified: True
    """
    if not pnr or not str(pnr).strip():
        return None

    clean_pnr = sanitize_payload(str(pnr).strip())
    if not clean_pnr or not re.fullmatch(r"^\d{10}$", clean_pnr):
        return None

    # 1. Check persistent database (pnr_tickets)
    try:
        from backend.database import get_pnr_ticket
        db_ticket = get_pnr_ticket(clean_pnr)
        if db_ticket:
            journey = db_ticket.get("journey", {})
            booking = db_ticket.get("booking", {})
            passenger = db_ticket.get("passenger", {})
            return {
                "pnr": clean_pnr,
                "passenger_name": str(passenger.get("name", "John Doe")),
                "passenger": passenger,
                "train_number": str(journey.get("train_number", "")),
                "train_name": str(journey.get("train_name", "")),
                "from_station": str(journey.get("from_station", "")),
                "to_station": str(journey.get("to_station", "")),
                "travel_date": str(journey.get("travel_date", "")),
                "departure_time": str(journey.get("departure_time", "")),
                "arrival_time": str(journey.get("arrival_time", "")),
                "coach": str(booking.get("coach", "")),
                "seat_number": str(booking.get("seat_number", "")),
                "berth_type": str(booking.get("berth_type", "")),
                "class_code": str(journey.get("class_code", "")),
                "class_name": str(journey.get("class_name", "")),
                "status": str(booking.get("status", "CNF")),
                "status_detail": str(booking.get("status_detail", "Confirmed / Allotted")),
                "fare": float(booking.get("fare", 1480.0) or 1480.0),
                "verification_status": "DEMO",
                "is_demo": True,
                "match_verified": True,
                "success": True,
                "ticket_id": db_ticket.get("ticket_id", f"IRCTC-{clean_pnr}"),
                "journey": journey,
                "booking": booking,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
    except Exception:
        pass

    # 2. Exact match in pre-seeded manifest
    if clean_pnr in KNOWN_TICKETS:
        rec = KNOWN_TICKETS[clean_pnr]
        journey = rec.get("journey", {})
        booking = rec.get("booking", {})
        passenger = rec.get("passenger", {})
        return {
            "pnr": clean_pnr,
            "passenger_name": str(passenger.get("name", "John Doe")),
            "passenger": passenger,
            "train_number": str(journey.get("train_number", "")),
            "train_name": str(journey.get("train_name", "")),
            "from_station": str(journey.get("from_station", "")),
            "to_station": str(journey.get("to_station", "")),
            "travel_date": str(journey.get("travel_date", "")),
            "departure_time": str(journey.get("departure_time", "")),
            "arrival_time": str(journey.get("arrival_time", "")),
            "coach": str(booking.get("coach", "")),
            "seat_number": str(booking.get("seat_number", "")),
            "berth_type": str(booking.get("berth_type", "")),
            "class_code": str(journey.get("class_code", "")),
            "class_name": str(journey.get("class_name", "")),
            "status": str(booking.get("status", "CNF")),
            "status_detail": str(booking.get("status_detail", "Confirmed / Allotted")),
            "fare": float(booking.get("fare", 1480.0) or 1480.0),
            "verification_status": "DEMO",
            "is_demo": True,
            "match_verified": True,
            "success": True,
            "ticket_id": rec.get("ticket_id", f"IRCTC-{clean_pnr}"),
            "journey": journey,
            "booking": booking,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    return None


def verify_ticket(payload: str) -> Dict[str, Any]:
    """
    Verifies a scanned ticket QR/barcode payload or 10-digit PNR against the database.
    Uses canonical verify_pnr provider as the single source of truth for PNR verification.
    If PNR does not exist, returns NOT_FOUND (never synthesizes fake demonstration data).
    """
    if not payload or not str(payload).strip():
        return {
            "status": "ERROR",
            "match_verified": False,
            "success": False,
            "message": "Empty or unreadable ticket payload received.",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    raw_clean = str(payload).strip()
    pnr_key = sanitize_payload(raw_clean)

    # 1. Canonical verify_pnr lookup
    pnr_match = verify_pnr(pnr_key)
    if pnr_match:
        data = pnr_match.copy()
        data["status"] = "SUCCESS"
        data["raw_payload"] = raw_clean
        data["security_hash"] = f"SHA256-IRCTC-{hash(pnr_key) & 0xFFFFFFF:07X}"
        return data

    # 2. Check by ticket_id exact match (e.g. from scanned barcode)
    for record in KNOWN_TICKETS.values():
        if pnr_key == record.get("ticket_id"):
            journey = record.get("journey", {})
            booking = record.get("booking", {})
            passenger = record.get("passenger", {})
            p_pnr = record.get("pnr", pnr_key)
            return {
                "pnr": p_pnr,
                "passenger_name": str(passenger.get("name", "John Doe")),
                "passenger": passenger,
                "train_number": str(journey.get("train_number", "")),
                "train_name": str(journey.get("train_name", "")),
                "from_station": str(journey.get("from_station", "")),
                "to_station": str(journey.get("to_station", "")),
                "travel_date": str(journey.get("travel_date", "")),
                "departure_time": str(journey.get("departure_time", "")),
                "arrival_time": str(journey.get("arrival_time", "")),
                "coach": str(booking.get("coach", "")),
                "seat_number": str(booking.get("seat_number", "")),
                "berth_type": str(booking.get("berth_type", "")),
                "class_code": str(journey.get("class_code", "")),
                "class_name": str(journey.get("class_name", "")),
                "status": "SUCCESS",
                "status_detail": str(booking.get("status_detail", "Confirmed / Allotted")),
                "fare": float(booking.get("fare", 1480.0) or 1480.0),
                "verification_status": "DEMO",
                "is_demo": True,
                "match_verified": True,
                "success": True,
                "ticket_id": record.get("ticket_id", pnr_key),
                "journey": journey,
                "booking": booking,
                "raw_payload": raw_clean,
                "security_hash": f"SHA256-IRCTC-{hash(pnr_key) & 0xFFFFFFF:07X}",
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }

    # 3. Strict rejection for random / unknown PNRs (NO fake demonstration data synthesis)
    return {
        "status": "NOT_FOUND",
        "match_verified": False,
        "success": False,
        "message": "PNR not found. Please check the PNR and try again.",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


