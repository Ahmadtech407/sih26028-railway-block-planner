"""
Asynchronous Optimizer Job Manager & Worker Architecture.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Decouples heavy OR-Tools CP-SAT solving from the FastAPI HTTP worker thread:
- API receives request and immediately enqueues a background job.
- ThreadPoolExecutor worker processes the mathematical optimization.
- Enforces strict solver execution timeouts (25 seconds).
- Emits AI_RECOMMENDED status (never APPROVED) and registers clearance record.
- Process-local job store with clean interface ready for Redis/Celery drop-in.
"""

import concurrent.futures
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.schemas.api_models import BlockOptimizationRequest, BlockOptimizationResponse
from backend.services.optimizer_service import solve_maintenance_block
from backend.services import clearance_service
from backend.schemas.clearance_models import ClearanceCreateRequest, ClearanceStateEnum

logger = logging.getLogger(__name__)

SOLVER_TIMEOUT_SECONDS = 25.0


class JobStatusEnum(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


class OptimizationJobRecord(BaseModel):
    job_id: str
    block_id: str
    section_id: str
    status: JobStatusEnum
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    result: Optional[BlockOptimizationResponse] = None
    error_message: Optional[str] = None
    architecture_note: str = (
        "Process-local asynchronous worker. Abstracted job interface ready for Redis/Celery distributed queues."
    )


# In-memory process-local job storage repository
_JOB_STORE: Dict[str, OptimizationJobRecord] = {}
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="or_tools_worker")


def _run_optimization_worker(job_id: str, request: BlockOptimizationRequest) -> None:
    """Worker task executed in background thread pool."""
    job = _JOB_STORE.get(job_id)
    if not job:
        return

    job.status = JobStatusEnum.RUNNING
    job.started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()

    try:
        # Execute CP-SAT optimization with timeout protection
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as sub_exec:
            future = sub_exec.submit(solve_maintenance_block, request)
            try:
                response = future.result(timeout=SOLVER_TIMEOUT_SECONDS)
                t1 = time.perf_counter()

                # Ensure result explicitly enforces AI_RECOMMENDED rather than auto-approval
                response.message = (
                    "AI recommendation computed via OR-Tools CP-SAT. "
                    "HUMAN AUTHORIZATION MANDATORY — AI recommendation cannot grant track possession."
                )

                job.status = JobStatusEnum.COMPLETED
                job.completed_at = datetime.now(timezone.utc).isoformat()
                job.duration_ms = round((t1 - t0) * 1000.0, 1)
                job.result = response

                # Automatically initialize or update clearance record in AI_RECOMMENDED state
                if response.allocated_start_min is not None and response.allocated_end_min is not None:
                    try:
                        clearance_service.create_clearance(
                            ClearanceCreateRequest(
                                block_id=request.block_id,
                                section_id=request.section_id,
                                duration_minutes=request.duration_minutes,
                                start_min=response.allocated_start_min,
                                end_min=response.allocated_end_min,
                                work_type=request.work_type or "Track Maintenance",
                                created_by="OR_TOOLS_AI_SOLVER",
                                initial_state=ClearanceStateEnum.AI_RECOMMENDED,
                                ai_note=(
                                    f"OR-Tools CP-SAT computed window {response.formatted_window} "
                                    f"with {response.safety_buffer_minutes}m safety buffer. Risk: {response.risk_level}."
                                ),
                            )
                        )
                    except Exception as exc:
                        logger.debug("Automatic clearance record creation warning: %s", exc)

            except concurrent.futures.TimeoutError:
                t1 = time.perf_counter()
                job.status = JobStatusEnum.TIMEOUT
                job.completed_at = datetime.now(timezone.utc).isoformat()
                job.duration_ms = round((t1 - t0) * 1000.0, 1)
                job.error_message = f"Solver exceeded {SOLVER_TIMEOUT_SECONDS}s execution deadline."

    except Exception as exc:
        t1 = time.perf_counter()
        job.status = JobStatusEnum.FAILED
        job.completed_at = datetime.now(timezone.utc).isoformat()
        job.duration_ms = round((t1 - t0) * 1000.0, 1)
        job.error_message = f"Optimization task failed: {str(exc)}"
        logger.error("Optimization job %s exception: %s", job_id, exc, exc_info=True)


def submit_optimization_job(request: BlockOptimizationRequest) -> OptimizationJobRecord:
    """Enqueues an optimization task and returns the initial QUEUED job record immediately."""
    job_id = f"JOB-OPT-{uuid.uuid4().hex[:10].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()

    record = OptimizationJobRecord(
        job_id=job_id,
        block_id=request.block_id,
        section_id=request.section_id,
        status=JobStatusEnum.QUEUED,
        created_at=now_iso,
    )
    _JOB_STORE[job_id] = record

    # Submit worker task to background executor
    _EXECUTOR.submit(_run_optimization_worker, job_id, request)
    return record


def get_job_status(job_id: str) -> Optional[OptimizationJobRecord]:
    """Retrieve current status and result for an optimization job."""
    return _JOB_STORE.get(job_id)


def list_recent_jobs(limit: int = 20) -> List[OptimizationJobRecord]:
    """List most recent optimization jobs."""
    jobs = list(_JOB_STORE.values())
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return jobs[:limit]
