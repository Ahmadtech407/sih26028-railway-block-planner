"""
RailTrack Database
Supabase PostgreSQL storage for passenger accounts, preferences, and railway metadata.
"""

import logging
from typing import Optional, Dict, Any, List

from backend.supa_client import supabase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Database initialization
# ---------------------------------------------------------

def init_database() -> None:
    """
    Supabase database initialization.
    Verifies connection and triggers master data sync if tables need seeding.
    """
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
    """Create a passenger account in Supabase and return its ID."""
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

        if not response.data:
            raise RuntimeError(
                f"Failed to create user in Supabase: {response.error}"
            )

        return int(response.data[0]["id"])
    except Exception as exc:
        logger.error("create_user failed: %s", exc)
        raise


# ---------------------------------------------------------
# Find user by identifier
# ---------------------------------------------------------

def get_user_by_identifier(
    identifier: str,
) -> Optional[Dict[str, Any]]:
    """Find a passenger account by email/mobile identifier."""
    try:
        response = (
            supabase
            .table("users")
            .select("id, name, identifier, password_hash, created_at")
            .eq("identifier", identifier)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return response.data[0]
    except Exception as exc:
        logger.error("get_user_by_identifier failed: %s", exc)
        return None


# ---------------------------------------------------------
# Find user by ID
# ---------------------------------------------------------

def get_user_by_id(
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """Find a passenger account by its ID."""
    try:
        response = (
            supabase
            .table("users")
            .select("id, name, identifier, created_at")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return response.data[0]
    except Exception as exc:
        logger.error("get_user_by_id failed: %s", exc)
        return None


# ---------------------------------------------------------
# User Management Extensions
# ---------------------------------------------------------

def list_users(limit: int = 50) -> List[Dict[str, Any]]:
    """List passenger accounts from Supabase (excluding password hashes)."""
    try:
        response = (
            supabase
            .table("users")
            .select("id, name, identifier, created_at")
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as exc:
        logger.error("list_users failed: %s", exc)
        return []


def get_user_count() -> int:
    """Return total count of registered passenger accounts."""
    try:
        response = supabase.table("users").select("id").execute()
        return len(response.data) if response.data else 0
    except Exception as exc:
        logger.error("get_user_count failed: %s", exc)
        return 0


def update_user_name(user_id: int, name: str) -> bool:
    """Update passenger's profile display name."""
    try:
        res = (
            supabase
            .table("users")
            .update({"name": name})
            .eq("id", user_id)
            .execute()
        )
        return bool(res.data)
    except Exception as exc:
        logger.error("update_user_name failed: %s", exc)
        return False


def update_user_password(user_id: int, password_hash: str) -> bool:
    """Update password hash for an existing account."""
    try:
        res = (
            supabase
            .table("users")
            .update({"password_hash": password_hash})
            .eq("id", user_id)
            .execute()
        )
        return bool(res.data)
    except Exception as exc:
        logger.error("update_user_password failed: %s", exc)
        return False


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