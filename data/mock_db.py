"""
Backward-compatibility alias for data.railway_reference_db.
All reference infrastructure and operational data is defined in data.railway_reference_db.
"""

from data.railway_reference_db import (  # noqa: F401
    SECTION_DB,
    TRAIN_SCHEDULE_DB,
    COMMITTED_BLOCKS,
)

__all__ = ["SECTION_DB", "TRAIN_SCHEDULE_DB", "COMMITTED_BLOCKS"]
