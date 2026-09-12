"""
Tool: Commit Block Schedule

Commits an approved maintenance block schedule to the central database.
In production, this would interface with the Track Management System (TMS).
"""

import json
import uuid
from datetime import datetime

from data.railway_reference_db import COMMITTED_BLOCKS


def commit_block_schedule(
    block_id: str,
    section_id: str,
    start_time: str,
    end_time: str,
) -> str:
    """Commits an approved maintenance block schedule to the central railway
    database. This is the final step after optimization and review.

    Args:
        block_id: The maintenance block ID (e.g., 'MNT-KNP-04').
        section_id: The track section code (e.g., 'KNP-PRYJ-SEC-B').
        start_time: Block start time in HH:MM format (e.g., '12:35').
        end_time: Block end time in HH:MM format (e.g., '14:35').
    """
    transaction_id = f"TXN-RAIL-{datetime.now().strftime('%Y')}-{uuid.uuid4().hex[:8].upper()}"

    record = {
        "block_id": block_id,
        "section_id": section_id,
        "start_time": start_time,
        "end_time": end_time,
        "committed_at": datetime.now().isoformat(),
        "transaction_id": transaction_id,
        "committed_by": "AI_SECTION_CONTROLLER",
        "status": "COMMITTED",
    }

    COMMITTED_BLOCKS.append(record)

    return json.dumps({
        "status": "SUCCESS",
        "message": (
            f"Block {block_id} on section {section_id} officially scheduled "
            f"for period {start_time} to {end_time}."
        ),
        "transaction_id": transaction_id,
        "committed_at": record["committed_at"],
        "caution_board_notice": (
            f"CAUTION: Maintenance block active on {section_id} from "
            f"{start_time} to {end_time}. All drivers to observe speed "
            f"restrictions and block indicators."
        ),
    }, indent=2)
