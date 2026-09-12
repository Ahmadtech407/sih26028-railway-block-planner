"""
Conflict Check Routes.
"""

from fastapi import APIRouter
from backend.schemas.api_models import ConflictCheckRequest, ConflictCheckResponse
from backend.services.optimizer_service import check_conflicts

router = APIRouter(prefix="/conflicts", tags=["Conflict Analysis"])


@router.post("/check", response_model=ConflictCheckResponse, summary="Detect train path conflicts")
async def detect_conflicts(request: ConflictCheckRequest):
    """
    Scans a proposed maintenance window against scheduled train paths and identifies
    critical overlaps (Tier 1/2) vs. minor secondary regulations.
    """
    return check_conflicts(request)
