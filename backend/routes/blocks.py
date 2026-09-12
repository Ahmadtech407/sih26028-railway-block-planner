"""
Block Commit & History Routes.
"""

import time
import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter
from backend.schemas.api_models import CommitBlockRequest, CommitBlockResponse
from backend.services.train_service import min_to_hhmm

router = APIRouter(prefix="/blocks", tags=["Block Scheduling & TMS Commit"])

# In-memory storage for committed blocks
COMMITTED_BLOCKS_STORE: List[Dict[str, Any]] = []


@router.post("/commit", response_model=CommitBlockResponse, summary="Commit approved maintenance schedule")
async def commit_block(request: CommitBlockRequest):
    """
    Officially records an approved maintenance block to the Central Railway TMS,
    generates an audit transaction ID, and creates safety caution board orders.
    """
    start_str = min_to_hhmm(request.start_min)
    end_str = min_to_hhmm(request.end_min)
    now_str = datetime.now().isoformat()
    txn_id = f"TXN-RAIL-{datetime.now().strftime('%Y')}-{uuid.uuid4().hex[:8].upper()}"

    caution_msg = (
        f"CAUTION ORDER: Track maintenance block active on section {request.section_id} "
        f"from {start_str} to {end_str}. Type: {request.work_type}. "
        f"Loco Pilots to observe strict speed restrictions and signaling indicators."
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

    COMMITTED_BLOCKS_STORE.append(record)
    return CommitBlockResponse(**record)


@router.get("", response_model=List[CommitBlockResponse], summary="List all committed blocks")
async def list_committed_blocks():
    """Retrieve history of all maintenance blocks committed during the active session."""
    return [CommitBlockResponse(**b) for b in COMMITTED_BLOCKS_STORE]
