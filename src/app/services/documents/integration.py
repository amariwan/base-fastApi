"""Integration entrypoint for the documents service."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["documents"])


class ValidateTemplateRequest(BaseModel):
    document_type: str = "docx"
    template_content: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


def _resolve_path(payload: dict[str, Any], path: str) -> bool:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


@router.post("/validate-template", summary="Validate a document template")
async def validate_template(request: ValidateTemplateRequest) -> dict[str, Any]:
    placeholders = re.findall(r"\{\{\s*([A-Za-z_][\w.]*)\s*\}\}", request.template_content or "")
    missing = [name for name in placeholders if not _resolve_path(request.payload or {}, name)]
    if not request.template_content:
        valid = False
        status = "INVALID"
    elif missing:
        valid = False
        status = "INVALID"
    else:
        valid = True
        status = "VALID"
    result: dict[str, Any] = {
        "valid": valid,
        "validation_status": status,
    }
    if not request.dry_run and request.template_content:
        result["rendered_output"] = request.template_content
    if request.dry_run:
        result.pop("rendered_output", None)
    return result


@router.get("/buildDoc/{job_id}", summary="Build a document")
async def build_doc(job_id: str) -> dict[str, Any]:
    raise HTTPException(
        status_code=404,
        detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found", "solution": "Provide a valid job id"},
    )


@router.get("/buildView/{job_id}", summary="Build a view")
async def build_view(job_id: str) -> dict[str, Any]:
    raise HTTPException(
        status_code=404,
        detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found", "solution": "Provide a valid job id"},
    )


def register_service() -> dict:
    return {
        "name": "documents",
        "routers": [router],
        "startup": [],
        "shutdown": [],
        "runtime_config": lambda: {"documents": {"enabled": True}},
    }