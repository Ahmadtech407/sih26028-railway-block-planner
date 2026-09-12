"""
Hooks: Audit Logging & Safety Guards

Lifecycle hooks for the Antigravity agent that provide:
- Pre-tool-call audit logging for regulatory traceability.
- Safety gate on commit_block_schedule to prevent accidental commits.
- Post-tool-call result logging for observability.
- Session lifecycle logging.
"""

import json
import logging
from datetime import datetime

from google.antigravity import types
from google.antigravity.hooks import hooks

logger = logging.getLogger("sih26028.audit")


# =========================================================================
# SESSION HOOKS
# =========================================================================

@hooks.on_session_start
async def on_session_start():
    """Logs when the agent session initialises."""
    logger.info(
        "[SESSION] AI Section Controller session started at %s",
        datetime.now().isoformat(),
    )


@hooks.on_session_end
async def on_session_end():
    """Logs when the agent session terminates."""
    logger.info(
        "[SESSION] AI Section Controller session ended at %s",
        datetime.now().isoformat(),
    )


# =========================================================================
# PRE-TOOL-CALL HOOK (Audit + Safety Gate)
# =========================================================================

@hooks.pre_tool_call_decide
async def audit_and_guard_tool_call(
    data: types.ToolCall,
) -> types.HookResult:
    """Inspects every tool call before execution.

    - Logs tool name and arguments for audit trail.
    - Adds a safety gate on commit_block_schedule: logs a WARNING-level
      notice (in production, this could require human confirmation).
    """
    tool_name = data.name
    tool_args = data.args

    # Audit log every tool invocation
    logger.info(
        "[AUDIT] Tool invoked: %s | Args: %s | Timestamp: %s",
        tool_name,
        json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args),
        datetime.now().isoformat(),
    )

    # Safety gate: warn on commit operations
    if tool_name == "commit_block_schedule":
        logger.warning(
            "[SAFETY GATE] commit_block_schedule called for block_id=%s. "
            "In production, this should require Section Controller sign-off.",
            tool_args.get("block_id", "UNKNOWN") if isinstance(tool_args, dict) else "UNKNOWN",
        )

    # Allow all tool calls to proceed
    return types.HookResult(allow=True)


# =========================================================================
# POST-TOOL-CALL HOOK (Result Logging)
# =========================================================================

@hooks.post_tool_call
async def log_tool_result(data):
    """Logs tool execution completion for observability."""
    logger.info("[AUDIT] Tool execution completed. Result type: %s", type(data).__name__)


# =========================================================================
# Export all hooks for registration in LocalAgentConfig
# =========================================================================

ALL_HOOKS = [
    on_session_start,
    on_session_end,
    audit_and_guard_tool_call,
    log_tool_result,
]
