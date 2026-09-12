"""
Block Optimization Routes.
"""

from fastapi import APIRouter
from backend.schemas.api_models import BlockOptimizationRequest, BlockOptimizationResponse
from backend.services.optimizer_service import solve_maintenance_block

router = APIRouter(prefix="/optimizer", tags=["OR-Tools Optimization"])


@router.post("/solve", response_model=BlockOptimizationResponse, summary="Solve optimal maintenance block window")
async def solve_block(request: BlockOptimizationRequest):
    """
    Uses Google OR-Tools CP-SAT discrete constraint solver to find mathematically optimal
    zero-conflict maintenance windows with safety buffers and secondary traffic impact evaluation.
    """
    return solve_maintenance_block(request)
