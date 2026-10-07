"""
Block Optimization Routes.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Provides both asynchronous job-style endpoints (QUEUED -> RUNNING -> COMPLETED)
and backward-compatible solve endpoints. All outputs are strictly AI_RECOMMENDED.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.schemas.api_models import BlockOptimizationRequest, BlockOptimizationResponse
from backend.services.optimizer_job_service import (
    OptimizationJobRecord,
    get_job_status,
    list_recent_jobs,
    submit_optimization_job,
)
from backend.services.optimizer_service import solve_maintenance_block

router = APIRouter(prefix="/optimizer", tags=["OR-Tools Optimization"])


@router.post(
    "/jobs",
    response_model=OptimizationJobRecord,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue asynchronous maintenance block optimization task",
)
async def create_optimization_job(request: BlockOptimizationRequest):
    """
    Submits an optimization task to the background solver worker pool.
    Returns immediately with QUEUED status and a job_id without blocking the ASGI worker.
    """
    return submit_optimization_job(request)


@router.get(
    "/jobs/{job_id}",
    response_model=OptimizationJobRecord,
    summary="Get optimization job status and result",
)
async def retrieve_job(job_id: str):
    """Poll the status and computed schedule of an optimization job (QUEUED, RUNNING, COMPLETED, FAILED, TIMEOUT)."""
    job = get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization job '{job_id}' not found.",
        )
    return job


@router.get(
    "/jobs",
    response_model=List[OptimizationJobRecord],
    summary="List recent optimization jobs",
)
async def list_jobs(limit: int = Query(20, ge=1, le=100)):
    """Retrieve history of recently submitted optimization tasks."""
    return list_recent_jobs(limit=limit)


@router.post(
    "/solve",
    response_model=BlockOptimizationResponse,
    summary="Solve optimal maintenance block window (Advisory DSS)",
)
async def solve_block(request: BlockOptimizationRequest):
    """
    Computes mathematical maintenance window via Google OR-Tools CP-SAT.
    
    SAFETY NOTICE:
    Output is strictly an AI Recommendation (AI_RECOMMENDED).
    This endpoint cannot grant official railway track possession clearance.
    All recommended slots require formal human approval via /api/clearance.
    """
    # Execute solve logic
    response = solve_maintenance_block(request)

    # Initialize clearance record in AI_RECOMMENDED status
    if response.allocated_start_min is not None and response.allocated_end_min is not None:
        from backend.services import clearance_service
        from backend.schemas.clearance_models import ClearanceCreateRequest, ClearanceStateEnum
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
                        f"OR-Tools CP-SAT suggested window {response.formatted_window} "
                        f"with {response.safety_buffer_minutes}m buffer. Status: AI_RECOMMENDED."
                    ),
                )
            )
        except Exception:
            pass

    response.message = (
        "AI recommendation successfully computed. "
        "NOTICE: AI recommendation only — human authorization required via /api/clearance before commit."
    )
    return response
