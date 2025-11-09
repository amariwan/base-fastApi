from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

from shared.utils.string_utils import to_camel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized pagination response payload."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    items_per_page: StrictInt = Field(..., ge=1, le=100)
    current_page: StrictInt = Field(..., ge=1)
    total_pages: StrictInt = Field(..., ge=1)
    total_count: StrictInt = Field(..., ge=0)
    skip_count: StrictInt = Field(..., ge=0)
    sort_by: StrictStr | None = Field(default=None, max_length=50)
    items: list[T]


__all__ = ["PaginatedResponse"]
