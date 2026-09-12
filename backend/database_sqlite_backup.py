"""
RailTrack Database
Supabase PostgreSQL storage for passenger accounts.
"""

from typing import Optional, Dict, Any

from backend.supa_client import supabase


# ---------------------------------------------------------
# Database initialization
# ---------------------------------------------------------

def init_database() -> None:
    """
    Supabase database initialization.

    Tables are created through the Supabase SQL Editor,
    so no local SQLite initialization is required here.
    """
    return None


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
        raise RuntimeError("Failed to create user in Supabase.")

    return int(response.data[0]["id"])


# ---------------------------------------------------------
# Find user by identifier
# ---------------------------------------------------------

def get_user_by_identifier(
    identifier: str,
) -> Optional[Dict[str, Any]]:
    """Find a passenger account by email/mobile identifier."""

    response = (
        supabase
        .table("users")
        .select(
            "id, name, identifier, password_hash, created_at"
        )
        .eq("identifier", identifier)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


# ---------------------------------------------------------
# Find user by ID
# ---------------------------------------------------------

def get_user_by_id(
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """Find a passenger account by its ID."""

    response = (
        supabase
        .table("users")
        .select(
            "id, name, identifier, created_at"
        )
        .eq("id", user_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]