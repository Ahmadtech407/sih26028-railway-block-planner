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
                    role TEXT DEFAULT 'VIEWER',
                    created_at INTEGER NOT NULL
                );
            """)
            try:
                cur.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'VIEWER';")
            except Exception:
                pass
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clearance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    block_id TEXT UNIQUE NOT NULL,
                    section_id TEXT NOT NULL,
                    track_id TEXT,
                    work_type TEXT,
                    allocated_window TEXT,
                    start_min INTEGER,
                    end_min INTEGER,
                    duration_minutes INTEGER,
                    current_state TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    approved_at TEXT,
                    rejected_at TEXT,
                    cancelled_at TEXT,
                    ai_recommendation_note TEXT,
                    details_json TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS approval_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    block_id TEXT NOT NULL,
                    clearance_id INTEGER,
                    action TEXT NOT NULL,
                    previous_state TEXT NOT NULL,
                    new_state TEXT NOT NULL,
                    role TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    comment TEXT,
                    timestamp TEXT NOT NULL
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pnr_sessions (
                    token TEXT PRIMARY KEY,
                    pnr TEXT NOT NULL,
                    train_number TEXT NOT NULL,
                    train_name TEXT NOT NULL,
                    travel_date TEXT,
                    from_station TEXT,
                    to_station TEXT,
                    coach TEXT NOT NULL,
                    seat_number TEXT NOT NULL,
                    berth_type TEXT,
                    class_code TEXT,
                    class_name TEXT,
                    verification_status TEXT DEFAULT 'DEMO',
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ohe_permits (
                    permit_id TEXT PRIMARY KEY,
                    block_id TEXT NOT NULL,
                    electrical_section_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    tpc_officer_id TEXT,
                    power_block_permit_no TEXT,
                    discharge_rod_locations TEXT,
                    requested_at TEXT,
                    confirmed_at TEXT,
                    permit_issued_at TEXT,
                    work_completed_at TEXT,
                    restored_at TEXT,
                    remarks TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tsr_records (
                    tsr_id TEXT PRIMARY KEY,
                    block_id TEXT,
                    section_id TEXT NOT NULL,
                    track_id TEXT NOT NULL,
                    start_km REAL NOT NULL,
                    end_km REAL NOT NULL,
                    max_speed_kmph REAL NOT NULL,
                    normal_speed_kmph REAL NOT NULL,
                    effective_from_iso TEXT NOT NULL,
                    effective_until_iso TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    issued_by TEXT NOT NULL,
                    status TEXT NOT NULL,
                    staged_recovery_json TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS track_machines (
                    machine_id TEXT PRIMARY KEY,
                    machine_type TEXT NOT NULL,
                    stabling_station TEXT NOT NULL,
                    transit_speed_kmph REAL NOT NULL,
                    transit_duration_min INTEGER NOT NULL,
                    setup_time_min INTEGER NOT NULL,
                    clearance_time_min INTEGER NOT NULL,
                    assigned_block_id TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS committed_blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT UNIQUE NOT NULL,
                    block_id TEXT NOT NULL,
                    section_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    work_type TEXT,
                    committed_at TEXT NOT NULL,
                    caution_board_notice TEXT,
                    committed_by TEXT
                );
            """)
            # Migrations for existing tables
            clearance_migrations = [
                "ALTER TABLE clearance_records ADD COLUMN ohe_permit_id TEXT;",
                "ALTER TABLE clearance_records ADD COLUMN ohe_isolation_confirmed INTEGER DEFAULT 0;",
                "ALTER TABLE clearance_records ADD COLUMN signaling_acknowledged INTEGER DEFAULT 0;",
                "ALTER TABLE clearance_records ADD COLUMN tsr_id TEXT;",
                "ALTER TABLE clearance_records ADD COLUMN machine_id TEXT;",
                "ALTER TABLE clearance_records ADD COLUMN expires_at TEXT;",
                "ALTER TABLE clearance_records ADD COLUMN invalidated_at TEXT;",
                "ALTER TABLE clearance_records ADD COLUMN invalidation_reason TEXT;",
                "ALTER TABLE clearance_records ADD COLUMN reopened_at TEXT;",
                "ALTER TABLE clearance_records ADD COLUMN reopened_by TEXT;",
                "ALTER TABLE pnr_sessions ADD COLUMN verification_status TEXT DEFAULT 'DEMO';",
            ]
            for mig in clearance_migrations:
                try:
                    cur.execute(mig)
                except Exception:
                    pass
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
    role: str = "VIEWER",
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
                        "role": role,
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
                "INSERT INTO users (name, identifier, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (name, identifier, password_hash, role, created_at),
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
                "status": "SUCCESS",
                "match_verified": True,
                "security_hash": "SHA256-IRCTC-1234567890",
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

# ---------------------------------------------------------
# Clearance & Multi-Department Approval Persistence
# ---------------------------------------------------------

def save_clearance_record(record: Dict[str, Any]) -> int:
    """Persist or update a maintenance block clearance record in SQLite & Supabase."""
    _init_sqlite_tables()
    block_id = record["block_id"]
    section_id = record.get("section_id", "KNP-PRYJ-SEC-B")
    track_id = record.get("track_id", "KNP-PRYJ-DN-MAIN")
    work_type = record.get("work_type", "Routine Maintenance")
    allocated_window = record.get("allocated_window")
    start_min = record.get("start_min")
    end_min = record.get("end_min")
    duration_minutes = record.get("duration_minutes", 120)
    current_state = str(record.get("current_state", "DRAFT"))
    created_by = record.get("created_by", "SYSTEM")
    created_at = record.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    updated_at = record.get("updated_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    approved_at = record.get("approved_at")
    rejected_at = record.get("rejected_at")
    cancelled_at = record.get("cancelled_at")
    ai_recommendation_note = record.get("ai_recommendation_note")
    details_json = json.dumps(record.get("details", {}))

    # 1. Supabase persistence if available
    if is_supabase_configured():
        try:
            supabase.table("clearance_records").upsert({
                "block_id": block_id,
                "section_id": section_id,
                "track_id": track_id,
                "work_type": work_type,
                "allocated_window": allocated_window,
                "current_state": current_state,
                "created_by": created_by,
                "updated_at": updated_at,
            }, on_conflict="block_id").execute()
        except Exception as exc:
            logger.debug("Supabase clearance record upsert warning: %s", exc)

    # 2. Local SQLite primary persistence
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO clearance_records (
                block_id, section_id, track_id, work_type, allocated_window,
                start_min, end_min, duration_minutes, current_state,
                created_by, created_at, updated_at, approved_at, rejected_at,
                cancelled_at, ai_recommendation_note, details_json,
                ohe_permit_id, ohe_isolation_confirmed, signaling_acknowledged,
                tsr_id, machine_id, expires_at, invalidated_at,
                invalidation_reason, reopened_at, reopened_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(block_id) DO UPDATE SET
                current_state=excluded.current_state,
                allocated_window=excluded.allocated_window,
                start_min=excluded.start_min,
                end_min=excluded.end_min,
                duration_minutes=excluded.duration_minutes,
                updated_at=excluded.updated_at,
                approved_at=excluded.approved_at,
                rejected_at=excluded.rejected_at,
                cancelled_at=excluded.cancelled_at,
                ai_recommendation_note=excluded.ai_recommendation_note,
                details_json=excluded.details_json,
                ohe_permit_id=excluded.ohe_permit_id,
                ohe_isolation_confirmed=excluded.ohe_isolation_confirmed,
                signaling_acknowledged=excluded.signaling_acknowledged,
                tsr_id=excluded.tsr_id,
                machine_id=excluded.machine_id,
                expires_at=excluded.expires_at,
                invalidated_at=excluded.invalidated_at,
                invalidation_reason=excluded.invalidation_reason,
                reopened_at=excluded.reopened_at,
                reopened_by=excluded.reopened_by
        """, (
            block_id, section_id, track_id, work_type, allocated_window,
            start_min, end_min, duration_minutes, current_state,
            created_by, created_at, updated_at, approved_at, rejected_at,
            cancelled_at, ai_recommendation_note, details_json,
            record.get("ohe_permit_id"),
            1 if record.get("ohe_isolation_confirmed") else 0,
            1 if record.get("signaling_acknowledged") else 0,
            record.get("tsr_id"),
            record.get("machine_id"),
            record.get("expires_at"),
            record.get("invalidated_at"),
            record.get("invalidation_reason"),
            record.get("reopened_at"),
            record.get("reopened_by"),
        ))
        conn.commit()
        return int(cur.lastrowid or 1)


def get_clearance_record(block_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve persistent clearance record for a block."""
    _init_sqlite_tables()
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, block_id, section_id, track_id, work_type, allocated_window,
                   start_min, end_min, duration_minutes, current_state,
                   created_by, created_at, updated_at, approved_at, rejected_at,
                   cancelled_at, ai_recommendation_note, details_json,
                   ohe_permit_id, ohe_isolation_confirmed, signaling_acknowledged,
                   tsr_id, machine_id, expires_at, invalidated_at,
                   invalidation_reason, reopened_at, reopened_by
            FROM clearance_records WHERE block_id = ? LIMIT 1
        """, (block_id,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        res["ohe_isolation_confirmed"] = bool(res.get("ohe_isolation_confirmed"))
        res["signaling_acknowledged"] = bool(res.get("signaling_acknowledged"))
        res["history"] = get_approval_history(block_id)
        return res


def list_clearance_records() -> List[Dict[str, Any]]:
    """List all persistent maintenance block clearance records."""
    _init_sqlite_tables()
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, block_id, section_id, track_id, work_type, allocated_window,
                   start_min, end_min, duration_minutes, current_state,
                   created_by, created_at, updated_at, approved_at, rejected_at,
                   cancelled_at, ai_recommendation_note,
                   ohe_permit_id, ohe_isolation_confirmed, signaling_acknowledged,
                   tsr_id, machine_id, expires_at, invalidated_at,
                   invalidation_reason, reopened_at, reopened_by
            FROM clearance_records ORDER BY updated_at DESC
        """, ())
        records = [dict(r) for r in cur.fetchall()]
        for rec in records:
            rec["ohe_isolation_confirmed"] = bool(rec.get("ohe_isolation_confirmed"))
            rec["signaling_acknowledged"] = bool(rec.get("signaling_acknowledged"))
            rec["history"] = get_approval_history(rec["block_id"])
        return records


# ---------------------------------------------------------
# OHE Traction Permit Persistence
# ---------------------------------------------------------

def save_ohe_permit(permit: Dict[str, Any]) -> str:
    """Upsert OHE power block isolation permit record."""
    _init_sqlite_tables()
    permit_id = str(permit["permit_id"])
    discharge_locs = json.dumps(permit.get("discharge_rod_locations", []))
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ohe_permits (
                permit_id, block_id, electrical_section_id, state,
                tpc_officer_id, power_block_permit_no, discharge_rod_locations,
                requested_at, confirmed_at, permit_issued_at,
                work_completed_at, restored_at, remarks
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(permit_id) DO UPDATE SET
                state=excluded.state,
                tpc_officer_id=excluded.tpc_officer_id,
                power_block_permit_no=excluded.power_block_permit_no,
                discharge_rod_locations=excluded.discharge_rod_locations,
                requested_at=excluded.requested_at,
                confirmed_at=excluded.confirmed_at,
                permit_issued_at=excluded.permit_issued_at,
                work_completed_at=excluded.work_completed_at,
                restored_at=excluded.restored_at,
                remarks=excluded.remarks
        """, (
            permit_id,
            permit.get("block_id", ""),
            permit.get("electrical_section_id", "OHE-DEFAULT"),
            str(permit.get("state", "NOT_REQUESTED")),
            permit.get("tpc_officer_id"),
            permit.get("power_block_permit_no"),
            discharge_locs,
            permit.get("requested_at"),
            permit.get("confirmed_at"),
            permit.get("permit_issued_at"),
            permit.get("work_completed_at"),
            permit.get("restored_at"),
            permit.get("remarks"),
        ))
        conn.commit()
    return permit_id


def get_ohe_permit(permit_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve OHE permit by ID."""
    _init_sqlite_tables()
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ohe_permits WHERE permit_id = ? LIMIT 1", (permit_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["discharge_rod_locations"] = json.loads(d.get("discharge_rod_locations") or "[]")
        except Exception:
            d["discharge_rod_locations"] = []
        return d


def get_ohe_permit_by_block(block_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve OHE permit associated with a block."""
    _init_sqlite_tables()
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ohe_permits WHERE block_id = ? ORDER BY requested_at DESC LIMIT 1", (block_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["discharge_rod_locations"] = json.loads(d.get("discharge_rod_locations") or "[]")
        except Exception:
            d["discharge_rod_locations"] = []
        return d


# ---------------------------------------------------------
# Temporary Speed Restriction (TSR) Persistence
# ---------------------------------------------------------

def save_tsr_record(tsr: Dict[str, Any]) -> str:
    """Upsert TSR record."""
    _init_sqlite_tables()
    tsr_id = str(tsr["tsr_id"])
    staged_json = json.dumps(tsr.get("staged_recovery_schedule", []))
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tsr_records (
                tsr_id, block_id, section_id, track_id, start_km, end_km,
                max_speed_kmph, normal_speed_kmph, effective_from_iso,
                effective_until_iso, reason, issued_by, status,
                staged_recovery_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tsr_id) DO UPDATE SET
                max_speed_kmph=excluded.max_speed_kmph,
                effective_until_iso=excluded.effective_until_iso,
                status=excluded.status,
                staged_recovery_json=excluded.staged_recovery_json
        """, (
            tsr_id,
            tsr.get("block_id"),
            tsr.get("section_id", "KNP-PRYJ-SEC-B"),
            tsr.get("track_id", "KNP-PRYJ-DN-MAIN"),
            float(tsr.get("start_km", 0.0)),
            float(tsr.get("end_km", 0.0)),
            float(tsr.get("max_speed_kmph", 30.0)),
            float(tsr.get("normal_speed_kmph", 130.0)),
            tsr.get("effective_from_iso", ""),
            tsr.get("effective_until_iso", ""),
            tsr.get("reason", "Post-maintenance speed restriction"),
            tsr.get("issued_by", "SYSTEM"),
            tsr.get("status", "ACTIVE"),
            staged_json,
            tsr.get("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ))
        conn.commit()
    return tsr_id


def get_tsr_record(tsr_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve TSR record by ID."""
    _init_sqlite_tables()
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM tsr_records WHERE tsr_id = ? LIMIT 1", (tsr_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["staged_recovery_schedule"] = json.loads(d.get("staged_recovery_json") or "[]")
        except Exception:
            d["staged_recovery_schedule"] = []
        return d


def list_active_tsrs(section_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List currently active TSR records."""
    _init_sqlite_tables()
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        if section_id:
            cur.execute("SELECT * FROM tsr_records WHERE section_id = ? AND status = 'ACTIVE'", (section_id,))
        else:
            cur.execute("SELECT * FROM tsr_records WHERE status = 'ACTIVE'")
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            try:
                r["staged_recovery_schedule"] = json.loads(r.get("staged_recovery_json") or "[]")
            except Exception:
                r["staged_recovery_schedule"] = []
        return rows


# ---------------------------------------------------------
# Committed Maintenance Blocks (TMS Audit) Persistence
# ---------------------------------------------------------

def save_committed_block(record: Dict[str, Any]) -> str:
    """Persist an officially committed maintenance block transaction."""
    _init_sqlite_tables()
    txn_id = str(record["transaction_id"])
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO committed_blocks (
                transaction_id, block_id, section_id, start_time, end_time,
                work_type, committed_at, caution_board_notice, committed_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            txn_id,
            record["block_id"],
            record["section_id"],
            record["start_time"],
            record["end_time"],
            record.get("work_type", "Track Maintenance"),
            record["committed_at"],
            record.get("caution_board_notice", ""),
            record.get("committed_by", "SYSTEM"),
        ))
        conn.commit()
    return txn_id


def list_committed_blocks_db(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve committed maintenance blocks from persistent database."""
    _init_sqlite_tables()
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT transaction_id, block_id, section_id, start_time, end_time,
                   work_type, committed_at, caution_board_notice
            FROM committed_blocks ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]


def add_approval_history(item: Dict[str, Any]) -> int:
    """Append an immutable approval audit entry to history."""
    _init_sqlite_tables()
    block_id = item["block_id"]
    action = item["action"]
    prev_state = str(item["previous_state"]) if item.get("previous_state") else "NONE" 
    new_state = str(item["new_state"])
    role = str(item["role"])
    user_id = str(item["user_id"])
    comment = item.get("comment")
    ts = item.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO approval_history (
                block_id, clearance_id, action, previous_state, new_state,
                role, user_id, comment, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            block_id, item.get("clearance_id"), action, prev_state, new_state,
            role, user_id, comment, ts
        ))
        conn.commit()
        return int(cur.lastrowid)


def get_approval_history(block_id: str) -> List[Dict[str, Any]]:
    """Retrieve chronological approval history audit trail for a block."""
    _init_sqlite_tables()
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, block_id, action, previous_state, new_state, role,
                   user_id, comment, timestamp
            FROM approval_history WHERE block_id = ? ORDER BY id ASC
        """, (block_id,))
        results = []
        for r in cur.fetchall():
            d = dict(r)
            if d.get("previous_state") in ("NONE", "None", ""):
                d["previous_state"] = None
            results.append(d)
        return results


def create_pnr_session(
    token: str,
    pnr: str,
    journey_data: Dict[str, Any],
    expires_at_iso: str,
    verification_status: str = "DEMO",
) -> None:
    """Store short-lived verified PNR session in persistent database."""
    _init_sqlite_tables()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    v_stat = str(verification_status or journey_data.get("verification_status") or "DEMO").upper()
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pnr_sessions (
                token, pnr, train_number, train_name, travel_date,
                from_station, to_station, coach, seat_number, berth_type,
                class_code, class_name, verification_status, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(token) DO UPDATE SET
                pnr=excluded.pnr,
                train_number=excluded.train_number,
                train_name=excluded.train_name,
                coach=excluded.coach,
                seat_number=excluded.seat_number,
                verification_status=excluded.verification_status,
                expires_at=excluded.expires_at
        """, (
            token,
            pnr,
            str(journey_data.get("train_number", "")),
            str(journey_data.get("train_name", "")),
            str(journey_data.get("travel_date", "")),
            str(journey_data.get("from_station", "")),
            str(journey_data.get("to_station", "")),
            str(journey_data.get("coach", "")),
            str(journey_data.get("seat_number", "")),
            str(journey_data.get("berth_type", "")),
            str(journey_data.get("class_code", "")),
            str(journey_data.get("class_name", "")),
            v_stat,
            now_iso,
            expires_at_iso,
        ))
        conn.commit()


def get_pnr_session(token: str) -> Optional[Dict[str, Any]]:
    """Retrieve verified PNR session by secure token if not expired."""
    _init_sqlite_tables()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT token, pnr, train_number, train_name, travel_date,
                   from_station, to_station, coach, seat_number, berth_type,
                   class_code, class_name, verification_status, created_at, expires_at
            FROM pnr_sessions
            WHERE token = ? AND expires_at > ?
            LIMIT 1
        """, (token, now_iso))
        row = cur.fetchone()
        if row:
            return dict(row)
    return None



def delete_pnr_session(token: str) -> bool:
    """Invalidate and remove a verified PNR session."""
    _init_sqlite_tables()
    with _get_sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM pnr_sessions WHERE token = ?", (token,))
        conn.commit()
        return cur.rowcount > 0

