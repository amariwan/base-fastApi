from __future__ import annotations

"""Pydantic models describing normalized JWT claims."""

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator


class UserClaims(BaseModel):
    """Normalized representation of the authenticated user."""

    model_config = ConfigDict(extra="allow")

    sub: StrictStr = Field(..., min_length=1)
    roles: list[StrictStr] = Field(default_factory=list)
    email: StrictStr | None = Field(default=None, max_length=320)
    name: StrictStr | None = Field(default=None, max_length=200)
    preferred_username: StrictStr | None = Field(default=None, max_length=100)
    organization: StrictStr | None = Field(default=None, max_length=200)
    mandant_id: StrictStr | None = Field(default=None, max_length=100)

    @field_validator("sub")
    @classmethod
    def validate_sub(cls, value: str) -> str:
        """Ensure the `sub` claim is not empty after trimming."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("sub_required")
        return cleaned

    @field_validator("roles")
    @classmethod
    def normalize_roles(cls, roles: list[str]) -> list[str]:
        """Deduplicate and lowercase role entries while preserving order."""
        seen: set[str] = set()
        normalized: list[str] = []
        for role in roles:
            lowered = role.strip().lower()
            if lowered and lowered not in seen:
                seen.add(lowered)
                normalized.append(lowered)
        return normalized


__all__ = ["UserClaims"]

