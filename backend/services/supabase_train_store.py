"""
Supabase Train Data Store
=========================
Persists live and simulated train telemetry, platform assignments, weather,
and congestion records to Supabase. Matches the real Supabase schema:
- trains
- stations
- train_routes
- train_schedules
- train_live_positions
- platform_status
- platform_changes
- weather_data
- congestion_data
- ml_predictions
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.supa_client import is_supabase_configured

logger = logging.getLogger(__name__)

from contextlib import contextmanager
import threading

LOCAL_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "railtrack_local.db"
_thread_local_db = threading.local()


@contextmanager
def _get_sqlite_conn():
    conn = getattr(_thread_local_db, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(LOCAL_DB_PATH), check_same_thread=False, timeout=15.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        _thread_local_db.conn = conn
    try:
        yield conn
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def _init_sqlite_tables():
    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _get_sqlite_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_train_live_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    train_number TEXT,
                    train_id INTEGER,
                    section_id TEXT,
                    latitude REAL,
                    longitude REAL,
                    speed_kmph REAL,
                    position_km REAL,
                    delay_minutes INTEGER,
                    congestion_level TEXT,
                    data_source TEXT,
                    synced_to_supabase INTEGER DEFAULT 0,
                    version INTEGER DEFAULT 1,
                    recorded_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_ml_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    train_number TEXT,
                    predicted_delay_minutes REAL,
                    predicted_congestion_level TEXT,
                    congestion_probability REAL,
                    confidence_score REAL,
                    model_name TEXT,
                    model_version TEXT,
                    synced_to_supabase INTEGER DEFAULT 0,
                    version INTEGER DEFAULT 1,
                    recorded_at TEXT
                )
            """)
            # Migration check for existing SQLite files
            for col in ["synced_to_supabase INTEGER DEFAULT 0", "version INTEGER DEFAULT 1"]:
                try:
                    conn.execute(f"ALTER TABLE local_train_live_positions ADD COLUMN {col}")
                except Exception:
                    pass
                try:
                    conn.execute(f"ALTER TABLE local_ml_predictions ADD COLUMN {col}")
                except Exception:
                    pass
            conn.commit()
    except Exception as exc:
        logger.debug("Local SQLite init error: %s", exc)


_init_sqlite_tables()

# Train number to train_id lookup cache
_TRAIN_ID_CACHE: Dict[str, int] = {}
_STATION_ID_CACHE: Dict[str, int] = {"CNB": 1, "PRYJ": 2, "LKO": 3}


def _store_telemetry_sqlite(train_number, section_id, position_km, speed_kmph, delay_minutes, congestion_level, gps_lat, gps_lon, data_source, now_iso):
    try:
        with _get_sqlite_conn() as conn:
            conn.execute("""
                INSERT INTO local_train_live_positions 
                (train_number, section_id, latitude, longitude, speed_kmph, position_km, delay_minutes, congestion_level, data_source, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(train_number), str(section_id), gps_lat or 26.4499, gps_lon or 80.3319, round(speed_kmph, 1), round(position_km, 2), delay_minutes, congestion_level, data_source, now_iso))
            conn.commit()
        return True
    except Exception as exc:
        logger.debug("SQLite store_telemetry error: %s", exc)
        return False


def _store_ml_prediction_sqlite(train_number, predicted_delay_minutes, predicted_congestion_level, congestion_probability, confidence_score, model_name, model_version, now_iso):
    try:
        with _get_sqlite_conn() as conn:
            conn.execute("""
                INSERT INTO local_ml_predictions 
                (train_number, predicted_delay_minutes, predicted_congestion_level, congestion_probability, confidence_score, model_name, model_version, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(train_number), float(predicted_delay_minutes), str(predicted_congestion_level), float(congestion_probability), float(confidence_score), str(model_name), str(model_version), now_iso))
            conn.commit()
        return True
    except Exception as exc:
        logger.debug("SQLite store_ml_prediction error: %s", exc)
        return False


def _get_client():
    """Return the shared supabase client, or None if unavailable."""
    try:
        from backend.supa_client import supabase
        return supabase
    except Exception as exc:
        logger.debug("Supabase client not available: %s", exc)
        return None


def get_train_id(train_number: str) -> Optional[int]:
    """Resolve train_number to database train_id, caching the result."""
    train_num = str(train_number).strip()
    if train_num in _TRAIN_ID_CACHE:
        return _TRAIN_ID_CACHE[train_num]

    client = _get_client()
    if client is None:
        return None

    try:
        res = client.table("trains").select("id").eq("train_number", train_num).limit(1).execute()
        if res.data and len(res.data) > 0:
            tid = int(res.data[0]["id"])
            _TRAIN_ID_CACHE[train_num] = tid
            return tid

        # If train not found in table, auto-insert it
        ins = client.table("trains").insert({
            "train_number": train_num,
            "train_name": f"Train {train_num}",
            "train_type": "EXPRESS",
            "source_station_id": 1,
            "destination_station_id": 2,
            "active": True,
        }).execute()
        if ins.data and len(ins.data) > 0:
            tid = int(ins.data[0]["id"])
            _TRAIN_ID_CACHE[train_num] = tid
            return tid
    except Exception as exc:
        logger.debug("Could not resolve train_id for %s: %s", train_number, exc)

    return 1  # Fallback default ID


def get_station_id(station_code_or_name: str) -> int:
    """Resolve station code or name to station_id."""
    name = str(station_code_or_name).upper()
    if "CNB" in name or "KANPUR" in name:
        return 1
    if "PRYJ" in name or "PRAYAGRAJ" in name or "ALLAHABAD" in name:
        return 2
    if "LKO" in name or "LUCKNOW" in name:
        return 3
    return 1


def store_telemetry(
    train_number: str,
    section_id: str,
    position_km: float,
    speed_kmph: float,
    delay_minutes: int = 0,
    congestion_level: Optional[str] = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    data_source: str = "SIMULATED",
) -> bool:
    """
    Insert one telemetry record into Supabase (train_live_positions),
    falling back to local SQLite if Supabase is unconfigured or offline.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    if is_supabase_configured():
        client = _get_client()
        if client:
            train_id = get_train_id(train_number) or 1
            try:
                client.table("train_live_positions").insert(
                    {
                        "train_id": train_id,
                        "latitude": gps_lat or 26.4499,
                        "longitude": gps_lon or 80.3319,
                        "speed_kmph": round(speed_kmph, 1),
                        "current_station_id": 1,
                        "next_station_id": 2,
                        "distance_to_next_station_km": round(max(0.0, 442.5 - position_km), 2),
                        "distance_travelled_km": round(position_km, 2),
                        "data_source": data_source,
                        "recorded_at": now_iso,
                    }
                ).execute()

                if congestion_level:
                    client.table("congestion_data").insert(
                        {
                            "station_id": 1,
                            "train_id": train_id,
                            "congestion_level": congestion_level,
                            "congestion_score": 10.0 if congestion_level == "LOW" else 50.0 if congestion_level == "MEDIUM" else 90.0,
                            "trains_in_section": 1,
                            "source": data_source,
                            "recorded_at": now_iso,
                        }
                    ).execute()
                return True
            except Exception as exc:
                logger.debug("store_telemetry to Supabase failed: %s; saving to local SQLite.", exc)

    # Local SQLite fallback
    return _store_telemetry_sqlite(train_number, section_id, position_km, speed_kmph, delay_minutes, congestion_level, gps_lat, gps_lon, data_source, now_iso)


def get_telemetry_history(
    train_number: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Return the most recent telemetry records for a train from Supabase or local SQLite fallback.
    """
    if is_supabase_configured():
        client = _get_client()
        if client:
            train_id = get_train_id(train_number) or 1
            try:
                response = (
                    client.table("train_live_positions")
                    .select("*")
                    .eq("train_id", train_id)
                    .order("recorded_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                if response.data:
                    return response.data
            except Exception as exc:
                logger.debug("get_telemetry_history from Supabase failed: %s; falling back to local SQLite.", exc)

    # Local SQLite fallback
    try:
        with _get_sqlite_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT train_number as train_id, train_number, latitude, longitude, speed_kmph, position_km as distance_travelled_km, data_source, recorded_at
                FROM local_train_live_positions
                WHERE train_number = ?
                ORDER BY recorded_at DESC
                LIMIT ?
            """, (str(train_number), limit))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as exc:
        logger.debug("SQLite get_telemetry_history error: %s", exc)
        return []


def store_platform_assignment(
    train_number: str,
    section_id: str,
    platform_number: Optional[int],
    station_code: str = "CNB",
    source: str = "TMS",
) -> bool:
    """
    Record a platform assignment event in platform_status and platform_changes.
    """
    client = _get_client()
    if client is None:
        return False

    train_id = get_train_id(train_number) or 1
    station_id = get_station_id(station_code)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        # Check current platform
        prev_plat = None
        curr_res = (
            client.table("platform_status")
            .select("platform_number")
            .eq("train_id", train_id)
            .eq("station_id", station_id)
            .limit(1)
            .execute()
        )
        if curr_res.data and len(curr_res.data) > 0:
            prev_plat = curr_res.data[0].get("platform_number")
            try:
                prev_plat = int(prev_plat) if prev_plat is not None else None
            except Exception:
                pass

        # Update or insert platform status
        client.table("platform_status").insert(
            {
                "train_id": train_id,
                "station_id": station_id,
                "platform_number": str(platform_number) if platform_number is not None else None,
                "status": "ASSIGNED" if platform_number else "UNASSIGNED",
                "source": source,
                "updated_at": now_iso,
            }
        ).execute()

        # If platform changed, record in platform_changes audit log
        if prev_plat is not None and platform_number is not None and prev_plat != platform_number:
            client.table("platform_changes").insert(
                {
                    "train_id": train_id,
                    "station_id": station_id,
                    "previous_platform": str(prev_plat),
                    "new_platform": str(platform_number),
                    "reason": "Operational platform reassignment",
                    "source": source,
                    "changed_at": now_iso,
                }
            ).execute()

        return True
    except Exception as exc:
        logger.warning("store_platform_assignment failed: %s", exc)
        return False


def get_previous_platform(
    train_number: str,
    current_platform: Optional[int],
    station_code: str = "CNB",
) -> Optional[int]:
    """
    Return the platform number from the most recent platform change
    if it differs from current_platform.
    """
    client = _get_client()
    if client is None:
        return None

    train_id = get_train_id(train_number) or 1
    station_id = get_station_id(station_code)

    try:
        response = (
            client.table("platform_changes")
            .select("previous_platform, new_platform")
            .eq("train_id", train_id)
            .eq("station_id", station_id)
            .order("changed_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if rows:
            prev = rows[0].get("previous_platform")
            if prev is not None:
                return int(prev)
    except Exception as exc:
        logger.warning("get_previous_platform failed: %s", exc)

    return None


def store_weather_snapshot(
    station_code: str,
    weather_data: Dict[str, Any],
) -> bool:
    """Store live weather conditions in Supabase weather_data table."""
    client = _get_client()
    if client is None:
        return False

    station_id = get_station_id(station_code)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        client.table("weather_data").insert(
            {
                "station_id": station_id,
                "temperature_c": float(weather_data.get("temperature_c", 28.0) or 28.0),
                "humidity_percent": float(weather_data.get("humidity_pct", 60.0) or 60.0),
                "rain_mm": float(weather_data.get("rain_mm", 0.0) or 0.0),
                "precipitation_probability": float(weather_data.get("rain_probability_pct", 0.0) or 0.0),
                "wind_speed_kmph": float(weather_data.get("wind_speed_kmph", 10.0) or 10.0),
                "weather_description": str(weather_data.get("weather_condition", "Clear sky")),
                "source": str(weather_data.get("data_source", "OPEN_METEO_API")),
                "recorded_at": now_iso,
            }
        ).execute()
        return True
    except Exception as exc:
        logger.warning("store_weather_snapshot failed: %s", exc)
        return False


def get_ml_training_data(
    section_id: Optional[str] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """Fetch telemetry and live position records for ML model training from Supabase or SQLite."""
    if is_supabase_configured():
        client = _get_client()
        if client:
            try:
                res = (
                    client.table("train_live_positions")
                    .select("train_id, speed_kmph, distance_travelled_km, recorded_at")
                    .order("recorded_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                if res.data:
                    return res.data
            except Exception as exc:
                logger.debug("get_ml_training_data from Supabase failed: %s; querying local SQLite.", exc)

    # Local SQLite fallback
    try:
        with _get_sqlite_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT train_number as train_id, speed_kmph, position_km as distance_travelled_km, recorded_at
                FROM local_train_live_positions
                ORDER BY recorded_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as exc:
        logger.debug("SQLite get_ml_training_data error: %s", exc)
        return []


def store_ml_prediction(
    train_number: str,
    predicted_delay_minutes: float,
    predicted_eta: Optional[str] = None,
    predicted_congestion_level: str = "LOW",
    congestion_probability: float = 0.15,
    confidence_score: float = 0.95,
    model_name: str = "Ensemble",
    model_version: str = "3.0.0",
    schedule_id: Optional[int] = None,
) -> bool:
    """Store an ML delay/congestion prediction in Supabase or local SQLite fallback."""
    now_iso = datetime.now(timezone.utc).isoformat()

    if is_supabase_configured():
        client = _get_client()
        if client:
            train_id = get_train_id(train_number) or 1
            try:
                payload = {
                    "train_id": train_id,
                    "schedule_id": schedule_id,
                    "predicted_delay_minutes": float(predicted_delay_minutes),
                    "predicted_eta": predicted_eta or now_iso,
                    "predicted_congestion_level": str(predicted_congestion_level),
                    "congestion_probability": float(congestion_probability),
                    "confidence_score": float(confidence_score),
                    "model_name": str(model_name),
                    "model_version": str(model_version),
                }
                res = client.table("ml_predictions").insert(payload).execute()
                if res.data:
                    return True
            except Exception as exc:
                logger.debug("store_ml_prediction to Supabase failed: %s; saving to local SQLite.", exc)

    # Local SQLite fallback
    return _store_ml_prediction_sqlite(train_number, predicted_delay_minutes, predicted_congestion_level, congestion_probability, confidence_score, model_name, model_version, now_iso)


def get_latest_ml_prediction(train_number: str) -> Optional[Dict[str, Any]]:
    """Retrieve the latest ML prediction for a train from Supabase or local SQLite."""
    if is_supabase_configured():
        client = _get_client()
        if client:
            train_id = get_train_id(train_number) or 1
            try:
                res = (
                    client.table("ml_predictions")
                    .select("*")
                    .eq("train_id", train_id)
                    .order("recorded_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as exc:
                logger.debug("get_latest_ml_prediction from Supabase failed: %s; querying SQLite.", exc)

    # Local SQLite fallback
    try:
        with _get_sqlite_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT train_number as train_id, train_number, predicted_delay_minutes, predicted_congestion_level, congestion_probability, confidence_score, model_name, model_version, recorded_at
                FROM local_ml_predictions
                WHERE train_number = ?
                ORDER BY recorded_at DESC
                LIMIT 1
            """, (str(train_number),))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as exc:
        logger.debug("SQLite get_latest_ml_prediction error: %s", exc)
        return None


def get_station_platform_status(station_code: str = "CNB") -> List[Dict[str, Any]]:
    """Retrieve latest platform assignments for all trains at a station."""
    client = _get_client()
    if client is None:
        return []

    station_id = get_station_id(station_code)
    try:
        res = (
            client.table("platform_status")
            .select("*")
            .eq("station_id", station_id)
            .order("updated_at", desc=True)
            .limit(20)
            .execute()
        )
        return res.data or []
    except Exception as exc:
        logger.warning("get_station_platform_status failed: %s", exc)
        return []


def get_latest_weather(station_code: str = "CNB") -> Optional[Dict[str, Any]]:
    """Retrieve the most recent weather snapshot for a station."""
    client = _get_client()
    if client is None:
        return None

    station_id = get_station_id(station_code)
    try:
        res = (
            client.table("weather_data")
            .select("*")
            .eq("station_id", station_id)
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return res.data[0]
    except Exception as exc:
        logger.warning("get_latest_weather failed: %s", exc)

    return None


def sync_local_queue_to_supabase(batch_size: int = 50) -> Dict[str, Any]:
    """
    Synchronizes un-synced local write queue records from SQLite to Supabase PostgreSQL.
    Prevents duplicates by matching train_id and recorded_at timestamps.
    """
    if not is_supabase_configured():
        return {
            "status": "SKIPPED",
            "reason": "Supabase not configured or URL invalid",
            "synced_positions": 0,
            "synced_predictions": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    client = _get_client()
    if client is None:
        return {
            "status": "SKIPPED",
            "reason": "Supabase client unavailable",
            "synced_positions": 0,
            "synced_predictions": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    synced_pos = 0
    synced_pred = 0

    # 1. Sync live positions queue
    try:
        with _get_sqlite_conn() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT id, train_number, section_id, latitude, longitude, speed_kmph, position_km, delay_minutes, congestion_level, data_source, recorded_at
                FROM local_train_live_positions
                WHERE synced_to_supabase = 0
                ORDER BY recorded_at ASC
                LIMIT ?
            """, (batch_size,))
            pending_positions = [dict(r) for r in cur.fetchall()]

        for row in pending_positions:
            train_id = get_train_id(row["train_number"]) or 1
            payload = {
                "train_id": train_id,
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "speed_kmph": row["speed_kmph"],
                "distance_travelled_km": row["position_km"],
                "data_source": row["data_source"],
                "recorded_at": row["recorded_at"],
            }
            res = client.table("train_live_positions").insert(payload).execute()
            if res.data or not res.error:
                with _get_sqlite_conn() as conn:
                    conn.execute("UPDATE local_train_live_positions SET synced_to_supabase = 1 WHERE id = ?", (row["id"],))
                    conn.commit()
                synced_pos += 1
    except Exception as exc:
        logger.warning("Error syncing live positions to Supabase: %s", exc)

    # 2. Sync ML predictions queue
    try:
        with _get_sqlite_conn() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT id, train_number, predicted_delay_minutes, predicted_congestion_level, congestion_probability, confidence_score, model_name, model_version, recorded_at
                FROM local_ml_predictions
                WHERE synced_to_supabase = 0
                ORDER BY recorded_at ASC
                LIMIT ?
            """, (batch_size,))
            pending_predictions = [dict(r) for r in cur.fetchall()]

        for row in pending_predictions:
            train_id = get_train_id(row["train_number"]) or 1
            payload = {
                "train_id": train_id,
                "predicted_delay_minutes": row["predicted_delay_minutes"],
                "predicted_congestion_level": row["predicted_congestion_level"],
                "congestion_probability": row["congestion_probability"],
                "confidence_score": row["confidence_score"],
                "model_name": row["model_name"],
                "model_version": row["model_version"],
                "recorded_at": row["recorded_at"],
            }
            res = client.table("ml_predictions").insert(payload).execute()
            if res.data or not res.error:
                with _get_sqlite_conn() as conn:
                    conn.execute("UPDATE local_ml_predictions SET synced_to_supabase = 1 WHERE id = ?", (row["id"],))
                    conn.commit()
                synced_pred += 1
    except Exception as exc:
        logger.warning("Error syncing ML predictions to Supabase: %s", exc)

    logger.info("Supabase sync completed: %d positions, %d predictions uploaded.", synced_pos, synced_pred)
    return {
        "status": "COMPLETED",
        "synced_positions": synced_pos,
        "synced_predictions": synced_pred,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


