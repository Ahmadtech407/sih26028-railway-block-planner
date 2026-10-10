"""
Block Commit & History Routes.

Indian Railways AI Section Controller & Block Planner (SIH26028).
ENFORCES HARD SAFETY GATE:
A maintenance block CANNOT be committed unless its persistent clearance record
has completed all departmental reviews, has confirmed OHE traction isolation,
and has reached APPROVED state.
Persists all committed blocks to the persistent SQLite database.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status

from backend import database as db
from backend.schemas.api_models import CommitBlockRequest, CommitBlockResponse
from backend.schemas.clearance_models import ClearanceStateEnum
from backend.services import clearance_service
from backend.services.train_service import min_to_hhmm

router = APIRouter(prefix="/blocks", tags=["Block Scheduling & TMS Commit"])

# In-memory storage mirrored with persistent DB
COMMITTED_BLOCKS_STORE: List[Dict[str, Any]] = []


@router.post(
    "/commit",
    response_model=CommitBlockResponse,
    summary="Commit approved maintenance schedule to TMS (Safety Gated)",
)
async def commit_block(request: CommitBlockRequest):
    """
    HARD SAFETY GATE:
    Officially records an approved maintenance block to the Central Railway TMS.
    REJECTS (403 Forbidden) if the block's persistent clearance state is NOT 'APPROVED',
    or if OHE electrical isolation has not been confirmed.
    AI recommendations and unreviewed drafts are strictly blocked from TMS possession.
    """
    # 1. Load persistent clearance record
    clearance = clearance_service.get_clearance(request.block_id)

    if not clearance:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Safety Gate Rejection: Maintenance block '{request.block_id}' cannot be committed. "
                "No clearance record exists. The block must be submitted through /api/clearance and "
                "receive multi-departmental approvals before TMS commit."
            ),
        )

    # 2. Hard verification of clearance state
    if clearance.current_state != ClearanceStateEnum.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Safety Gate Rejection: Maintenance block '{request.block_id}' cannot be committed. "
                f"Current clearance state is '{clearance.current_state.value}'. "
                "Mandatory operational, engineering, and traction reviews must reach 'APPROVED' before TMS possession. "
                "AI recommendations cannot independently authorize track possession."
            ),
        )

    # 3. Verification of OHE Power Block Isolation
    if not clearance.ohe_isolation_confirmed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Safety Gate Rejection: Maintenance block '{request.block_id}' cannot be committed. "
                "Traction Power (OHE) 25 kV AC isolation is not confirmed. "
                "A verified Permit-to-Work from the Traction Power Controller is required."
            ),
        )

    start_str = min_to_hhmm(request.start_min)
    end_str = min_to_hhmm(request.end_min)
    now_str = datetime.now(timezone.utc).isoformat()
    txn_id = f"TXN-RAIL-{datetime.now().strftime('%Y')}-{uuid.uuid4().hex[:8].upper()}"

    caution_msg = (
        f"OFFICIAL CAUTION ORDER: Track possession granted on section {request.section_id} "
        f"from {start_str} to {end_str}. Type: {request.work_type}. "
        f"Multi-department clearance verified. Section isolation active."
    )

    record = {
        "status": "SUCCESS",
        "transaction_id": txn_id,
        "block_id": request.block_id,
        "section_id": request.section_id,
        "start_time": start_str,
        "end_time": end_str,
        "committed_at": now_str,
        "caution_board_notice": caution_msg,
    }

    # Persist to DB and memory mirror
    db.save_committed_block(record)
    COMMITTED_BLOCKS_STORE.append(record)
    return CommitBlockResponse(**record)


@router.get("", response_model=List[CommitBlockResponse], summary="List all committed blocks")
async def list_committed_blocks():
    """Retrieve history of all maintenance blocks officially committed to TMS."""
    db_records = db.list_committed_blocks_db()
    if db_records:
        formatted = []
        for r in db_records:
            formatted.append({
                "status": "SUCCESS",
                "transaction_id": r["transaction_id"],
                "block_id": r["block_id"],
                "section_id": r["section_id"],
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "committed_at": r["committed_at"],
                "caution_board_notice": r.get("caution_board_notice", ""),
            })
        return [CommitBlockResponse(**b) for b in formatted]
    return [CommitBlockResponse(**b) for b in COMMITTED_BLOCKS_STORE]
