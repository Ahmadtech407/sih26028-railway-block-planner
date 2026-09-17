"""
RailTrack Database
Supabase PostgreSQL storage for passenger accounts, preferences, and railway metadata,
with seamless local SQLite fallback for resilient offline/prototyping operations.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from backend.supa_client import supabase, is_supabase_configured

logger = logging.getLogger(__name__)

SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "railtrack.db"


def _get_sqlite_conn() -> sqlite3.Connection:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_sqlite_tables() -> None:
    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    identifier TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_journeys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    pnr TEXT NOT NULL,
                    ticket_json TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pnr_tickets (
                    pnr TEXT PRIMARY KEY,
                    ticket_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
            """)
            conn.commit()
            _seed_demo_pnr_tickets(conn)
    except Exception as exc:
        logger.warning("SQLite table init warning: %s", exc)


# ---------------------------------------------------------
# Database initialization
# ---------------------------------------------------------

def init_database() -> None:
    """
    Database initialization.
    Ensures local SQLite tables exist and checks Supabase master data sync.
    """
    _init_sqlite_tables()
    if is_supabase_configured():
        try:
            res = supabase.table("stations").select("id").limit(1).execute()
            if not res.data:
                from backend.services.supabase_sync import sync_all
                logger.info("Initializing Supabase master railway data...")
                sync_all()
        except Exception as exc:
            logger.warning("Supabase connection check during init_database: %s", exc)


# ---------------------------------------------------------
# User creation
# ---------------------------------------------------------

def create_user(
    name: str,
    identifier: str,
    password_hash: str,
    created_at: int,
) -> int:
    """Create a passenger account in Supabase (if configured) or SQLite fallback and return its ID."""
    _init_sqlite_tables()

    # If Supabase is configured, try Supabase first
    if is_supabase_configured():
        try:
            response = (
                supabase
                .table("users")
                .insert(
                    {
                        "name": name,
                        "identifier": identifier,
                        "password_hash": password_hash,
                        "created_at": created_at,
                    }
                )
                .execute()
            )
            if response.data:
                user_id = int(response.data[0]["id"])
                # Mirror to local SQLite for offline parity
                try:
                    with _get_sqlite_conn() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT OR IGNORE INTO users (id, name, identifier, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                            (user_id, name, identifier, password_hash, created_at),
                        )
                        conn.commit()
                except Exception:
                    pass
                return user_id
        except Exception as exc:
            logger.warning("Supabase create_user failed, falling back to SQLite: %s", exc)

    # Local SQLite storage fallback
    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (name, identifier, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (name, identifier, password_hash, created_at),
            )
            conn.commit()
            return int(cur.lastrowid)
    except Exception as exc:
        logger.error("create_user SQLite failed: %s", exc)
        raise


# ---------------------------------------------------------
# Find user by identifier
# ---------------------------------------------------------

def get_user_by_identifier(
    identifier: str,
) -> Optional[Dict[str, Any]]:
    """Find a passenger account by email/mobile identifier."""
    _init_sqlite_tables()

    if is_supabase_configured():
        try:
            response = (
                supabase
                .table("users")
                .select("id, name, identifier, password_hash, created_at")
                .eq("identifier", identifier)
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0]
        except Exception as exc:
            logger.warning("Supabase get_user_by_identifier failed: %s", exc)

    # Local SQLite fallback
    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, name, identifier, password_hash, created_at FROM users WHERE identifier = ? LIMIT 1",
                (identifier,),
            )
            row = cur.fetchone()
            if row:
                return dict(row)
    except Exception as exc:
        logger.error("get_user_by_identifier SQLite failed: %s", exc)

    return None


# ---------------------------------------------------------
# Find user by ID
# ---------------------------------------------------------

def get_user_by_id(
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """Find a passenger account by its ID."""
    _init_sqlite_tables()

    if is_supabase_configured():
        try:
            response = (
                supabase
                .table("users")
                .select("id, name, identifier, created_at")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0]
        except Exception as exc:
            logger.warning("Supabase get_user_by_id failed: %s", exc)

    # Local SQLite fallback
    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, name, identifier, created_at FROM users WHERE id = ? LIMIT 1",
                (user_id,),
            )
            row = cur.fetchone()
            if row:
                return dict(row)
    except Exception as exc:
        logger.error("get_user_by_id SQLite failed: %s", exc)

    return None


# ---------------------------------------------------------
# Journey Management Extensions
# ---------------------------------------------------------

def save_user_journey(user_id: int, pnr: str, ticket_data: Dict[str, Any]) -> bool:
    """Save or update passenger journey associated with user."""
    _init_sqlite_tables()
    payload_str = json.dumps(ticket_data)
    now_ts = int(time.time())

    # Attempt Supabase if configured
    if is_supabase_configured():
        try:
            supabase.table("user_journeys").upsert(
                {
                    "user_id": user_id,
                    "pnr": pnr,
                    "ticket_json": payload_str,
                    "updated_at": now_ts,
                },
                on_conflict="user_id",
            ).execute()
        except Exception as exc:
            logger.warning("Supabase save_user_journey warning: %s", exc)

    # SQLite persistent storage
    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO user_journeys (user_id, pnr, ticket_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    pnr = excluded.pnr,
                    ticket_json = excluded.ticket_json,
                    updated_at = excluded.updated_at
                """,
                (user_id, pnr, payload_str, now_ts),
            )
            conn.commit()
            return True
    except Exception as exc:
        logger.error("save_user_journey SQLite error: %s", exc)
        return False


def get_user_journey(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve saved journey details for user."""
    _init_sqlite_tables()

    if is_supabase_configured():
        try:
            res = (
                supabase
                .table("user_journeys")
                .select("ticket_json")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if res.data and res.data[0].get("ticket_json"):
                raw = res.data[0]["ticket_json"]
                return json.loads(raw) if isinstance(raw, str) else raw
        except Exception as exc:
            logger.warning("Supabase get_user_journey warning: %s", exc)

    # SQLite persistent storage
    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT ticket_json FROM user_journeys WHERE user_id = ? LIMIT 1",
                (user_id,),
            )
            row = cur.fetchone()
            if row and row["ticket_json"]:
                return json.loads(row["ticket_json"])
    except Exception as exc:
        logger.error("get_user_journey SQLite error: %s", exc)

    return None


def clear_user_journey(user_id: int) -> bool:
    """Disassociate / remove journey for user."""
    _init_sqlite_tables()

    if is_supabase_configured():
        try:
            supabase.table("user_journeys").delete().eq("user_id", user_id).execute()
        except Exception as exc:
            logger.warning("Supabase clear_user_journey warning: %s", exc)

    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM user_journeys WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
    except Exception as exc:
        logger.error("clear_user_journey SQLite error: %s", exc)
        return False


# ---------------------------------------------------------
# User Management Extensions
# ---------------------------------------------------------

def list_users(limit: int = 50) -> List[Dict[str, Any]]:
    """List passenger accounts from database (excluding password hashes)."""
    _init_sqlite_tables()

    if is_supabase_configured():
        try:
            response = (
                supabase
                .table("users")
                .select("id, name, identifier, created_at")
                .order("id", desc=True)
                .limit(limit)
                .execute()
            )
            if response.data:
                return response.data
        except Exception as exc:
            logger.warning("Supabase list_users warning: %s", exc)

    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, name, identifier, created_at FROM users ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        logger.error("list_users SQLite error: %s", exc)
        return []


def get_user_count() -> int:
    """Return total count of registered passenger accounts."""
    _init_sqlite_tables()

    if is_supabase_configured():
        try:
            response = supabase.table("users").select("id").execute()
            if response.data:
                return len(response.data)
        except Exception as exc:
            logger.warning("Supabase get_user_count warning: %s", exc)

    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM users")
            return int(cur.fetchone()[0])
    except Exception as exc:
        logger.error("get_user_count SQLite error: %s", exc)
        return 0


def update_user_name(user_id: int, name: str) -> bool:
    """Update passenger's profile display name."""
    _init_sqlite_tables()

    if is_supabase_configured():
        try:
            res = (
                supabase
                .table("users")
                .update({"name": name})
                .eq("id", user_id)
                .execute()
            )
            if res.data:
                pass
        except Exception as exc:
            logger.warning("Supabase update_user_name warning: %s", exc)

    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
            conn.commit()
            return cur.rowcount > 0
    except Exception as exc:
        logger.error("update_user_name SQLite error: %s", exc)
        return False


def update_user_password(user_id: int, password_hash: str) -> bool:
    """Update password hash for an existing account."""
    _init_sqlite_tables()

    if is_supabase_configured():
        try:
            res = (
                supabase
                .table("users")
                .update({"password_hash": password_hash})
                .eq("id", user_id)
                .execute()
            )
            if res.data:
                pass
        except Exception as exc:
            logger.warning("Supabase update_user_password warning: %s", exc)

    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
            conn.commit()
            return cur.rowcount > 0
    except Exception as exc:
        logger.error("update_user_password SQLite error: %s", exc)
        return False




def _seed_demo_pnr_tickets(conn: sqlite3.Connection) -> None:
    """Pre-seed controlled demonstration tickets into pnr_tickets database table."""
    try:
        cur = conn.cursor()
        # Demo tickets definition matching verified railway records
        demo_manifest = {
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
                "status": "SUCCESS",
                "match_verified": True,
                "security_hash": "SHA256-IRCTC-8429103847",
            },
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
                "status": "SUCCESS",
                "match_verified": True,
                "security_hash": "SHA256-IRCTC-8410000477",
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
                "status": "SUCCESS",
                "match_verified": True,
                "security_hash": "SHA256-IRCTC-2840192841",
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
                "status": "SUCCESS",
                "match_verified": True,
                "security_hash": "SHA256-IRCTC-9812401823",
            },
        }

        now_ts = int(time.time())
        for pnr_val, t_dict in demo_manifest.items():
            cur.execute(
                """
                INSERT INTO pnr_tickets (pnr, ticket_json, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(pnr) DO UPDATE SET ticket_json = excluded.ticket_json
                """,
                (pnr_val, json.dumps(t_dict), now_ts),
            )
        # Pre-seed official demonstration account if not already present
        cur.execute("SELECT id FROM users WHERE identifier = 'demo@railtrack.in' LIMIT 1")
        demo_user = cur.fetchone()
        if not demo_user:
            from backend.routes.auth import hash_password
            demo_pw_hash = hash_password("Demo@1234")
            cur.execute(
                "INSERT INTO users (name, identifier, password_hash, created_at) VALUES (?, ?, ?, ?)",
                ("John Doe", "demo@railtrack.in", demo_pw_hash, now_ts)
            )
            demo_user_id = cur.lastrowid
        else:
            demo_user_id = demo_user[0]

        # Attach controlled demonstration ticket to demo passenger account
        demo_ticket_json = json.dumps(demo_manifest["8429103847"])
        cur.execute(
            """
            INSERT INTO user_journeys (user_id, pnr, ticket_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET pnr = excluded.pnr, ticket_json = excluded.ticket_json
            """,
            (demo_user_id, "8429103847", demo_ticket_json, now_ts)
        )

        conn.commit()
    except Exception as exc:
        logger.warning("Error seeding demo PNR tickets: %s", exc)


def get_pnr_ticket(pnr: str) -> Optional[Dict[str, Any]]:
    """Retrieve ticket details from database by 10-digit PNR."""
    _init_sqlite_tables()
    pnr_clean = str(pnr).strip()

    if is_supabase_configured():
        try:
            res = supabase.table("pnr_tickets").select("ticket_json").eq("pnr", pnr_clean).limit(1).execute()
            if res.data and res.data[0].get("ticket_json"):
                raw = res.data[0]["ticket_json"]
                return json.loads(raw) if isinstance(raw, str) else raw
        except Exception as exc:
            logger.warning("Supabase get_pnr_ticket warning: %s", exc)

    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT ticket_json FROM pnr_tickets WHERE pnr = ? LIMIT 1", (pnr_clean,))
            row = cur.fetchone()
            if row and row["ticket_json"]:
                return json.loads(row["ticket_json"])
    except Exception as exc:
        logger.error("get_pnr_ticket SQLite error: %s", exc)

    return None


def save_pnr_ticket(pnr: str, ticket_data: Dict[str, Any]) -> bool:
    """Save or update ticket details in database by PNR."""
    _init_sqlite_tables()
    pnr_clean = str(pnr).strip()
    payload_str = json.dumps(ticket_data)
    now_ts = int(time.time())

    if is_supabase_configured():
        try:
            supabase.table("pnr_tickets").upsert(
                {"pnr": pnr_clean, "ticket_json": payload_str, "created_at": now_ts},
                on_conflict="pnr",
            ).execute()
        except Exception as exc:
            logger.warning("Supabase save_pnr_ticket warning: %s", exc)

    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO pnr_tickets (pnr, ticket_json, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(pnr) DO UPDATE SET ticket_json = excluded.ticket_json
                """,
                (pnr_clean, payload_str, now_ts),
            )
            conn.commit()
            return True
    except Exception as exc:
        logger.error("save_pnr_ticket SQLite error: %s", exc)
        return False


def list_pnr_tickets() -> List[Dict[str, Any]]:
    """List all verified PNR tickets in database."""
    _init_sqlite_tables()
    try:
        with _get_sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT ticket_json FROM pnr_tickets ORDER BY pnr ASC")
            return [json.loads(row["ticket_json"]) for row in cur.fetchall() if row["ticket_json"]]
    except Exception as exc:
        logger.error("list_pnr_tickets SQLite error: %s", exc)
        return []

# ---------------------------------------------------------
# Master Data Queries
# ---------------------------------------------------------

def get_stations_from_db() -> List[Dict[str, Any]]:
    """Fetch list of all stations from Supabase."""
    try:
        res = supabase.table("stations").select("*").order("id", desc=False).execute()
        return res.data or []
    except Exception as exc:
        logger.error("get_stations_from_db failed: %s", exc)
        return []


def get_trains_from_db(active_only: bool = True) -> List[Dict[str, Any]]:
    """Fetch operational trains from Supabase."""
    try:
        q = supabase.table("trains").select("*")
        if active_only:
            q = q.eq("active", "true")
        res = q.order("train_number", desc=False).execute()
        return res.data or []
    except Exception as exc:
        logger.error("get_trains_from_db failed: %s", exc)
        return []


def get_train_routes_from_db(train_number: str) -> List[Dict[str, Any]]:
    """Fetch ordered stop schedule for a specific train."""
    try:
        # Resolve train ID
        t_res = supabase.table("trains").select("id").eq("train_number", train_number).limit(1).execute()
        if not t_res.data:
            return []
        train_id = t_res.data[0]["id"]

        res = (
            supabase
            .table("train_routes")
            .select("station_sequence, station_id, arrival_time, departure_time, scheduled_platform")
            .eq("train_id", train_id)
            .order("station_sequence", desc=False)
            .execute()
        )
        return res.data or []
    except Exception as exc:
        logger.error("get_train_routes_from_db failed: %s", exc)
        return []
