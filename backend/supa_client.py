"""
RailTrack Supabase Client
Provides a robust, unified interface to Supabase PostgreSQL storage.
Supports both official supabase-py and built-in direct PostgREST REST client adapter.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Ensure .env is loaded regardless of current working directory
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")


class SupabaseResponse:
    """Standardized response object matching supabase-py API."""
    def __init__(self, data: Any = None, count: Optional[int] = None, error: Any = None):
        self.data = data
        self.count = count
        self.error = error

    def __repr__(self) -> str:
        return f"<SupabaseResponse data={len(self.data) if isinstance(self.data, list) else self.data} error={self.error}>"


class TableQuery:
    """Fluent PostgREST query builder replicating the supabase-py table API."""
    def __init__(self, base_url: str, key: str, table_name: str):
        self.endpoint = f"{base_url.rstrip('/')}/rest/v1/{table_name}"
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self.params: Dict[str, Any] = {}
        self.method = "GET"
        self.payload: Optional[Any] = None

    def select(self, columns: str = "*") -> "TableQuery":
        self.method = "GET"
        self.params["select"] = columns
        return self

    def insert(self, record: Any) -> "TableQuery":
        self.method = "POST"
        self.payload = record
        return self

    def update(self, values: Dict[str, Any]) -> "TableQuery":
        self.method = "PATCH"
        self.payload = values
        return self

    def upsert(self, record: Any, on_conflict: Optional[str] = None) -> "TableQuery":
        self.method = "POST"
        self.payload = record
        self.headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        if on_conflict:
            self.params["on_conflict"] = on_conflict
        return self

    def delete(self) -> "TableQuery":
        self.method = "DELETE"
        return self

    def eq(self, column: str, value: Any) -> "TableQuery":
        self.params[column] = f"eq.{value}"
        return self

    def neq(self, column: str, value: Any) -> "TableQuery":
        self.params[column] = f"neq.{value}"
        return self

    def gt(self, column: str, value: Any) -> "TableQuery":
        self.params[column] = f"gt.{value}"
        return self

    def gte(self, column: str, value: Any) -> "TableQuery":
        self.params[column] = f"gte.{value}"
        return self

    def lt(self, column: str, value: Any) -> "TableQuery":
        self.params[column] = f"lt.{value}"
        return self

    def lte(self, column: str, value: Any) -> "TableQuery":
        self.params[column] = f"lte.{value}"
        return self

    def in_(self, column: str, values: List[Any]) -> "TableQuery":
        formatted_vals = ",".join(str(v) for v in values)
        self.params[column] = f"in.({formatted_vals})"
        return self

    def is_(self, column: str, value: Any) -> "TableQuery":
        self.params[column] = f"is.{value}"
        return self

    def order(self, column: str, desc: bool = False) -> "TableQuery":
        direction = "desc" if desc else "asc"
        self.params["order"] = f"{column}.{direction}"
        return self

    def limit(self, count: int) -> "TableQuery":
        self.params["limit"] = str(count)
        return self

    def execute(self) -> SupabaseResponse:
        import requests
        try:
            if self.method == "GET":
                res = requests.get(self.endpoint, headers=self.headers, params=self.params, timeout=12)
            elif self.method == "POST":
                res = requests.post(self.endpoint, headers=self.headers, json=self.payload, params=self.params, timeout=12)
            elif self.method == "PATCH":
                res = requests.patch(self.endpoint, headers=self.headers, json=self.payload, params=self.params, timeout=12)
            elif self.method == "DELETE":
                res = requests.delete(self.endpoint, headers=self.headers, params=self.params, timeout=12)
            else:
                raise ValueError(f"Unsupported method: {self.method}")

            if res.status_code in (200, 201):
                try:
                    data = res.json()
                except Exception:
                    data = []
                return SupabaseResponse(data=data)
            elif res.status_code == 204:
                return SupabaseResponse(data=[])
            else:
                logger.warning("Supabase REST call failed [%s]: %s", res.status_code, res.text)
                return SupabaseResponse(data=None, error=res.text)
        except Exception as e:
            logger.error("Supabase REST error: %s", e)
            return SupabaseResponse(data=None, error=str(e))


class SupabaseRestClient:
    """Supabase Client adapter implementing the table() method."""
    def __init__(self, url: str, key: str):
        self.url = url or ""
        self.key = key or ""

    def table(self, table_name: str) -> TableQuery:
        return TableQuery(self.url, self.key, table_name)


# Initialize client: prefer official supabase SDK if present, fallback to built-in REST client
supabase = None

try:
    from supabase import create_client  # type: ignore
    if SUPABASE_URL and SUPABASE_SECRET_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
except Exception:
    pass

if supabase is None:
    supabase = SupabaseRestClient(SUPABASE_URL or "", SUPABASE_SECRET_KEY or "")