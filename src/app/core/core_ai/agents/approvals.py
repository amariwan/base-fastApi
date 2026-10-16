"""Trusted approval checks for side-effecting agent tools."""

from app.core.core_ai.contracts import ToolApprovalRequiredError


def require_approval(tool_name: str, *, required: bool, approved_tools: frozenset[str]) -> None:
    if required and tool_name not in approved_tools:
        raise ToolApprovalRequiredError(f"Tool '{tool_name}' requires trusted application approval")
