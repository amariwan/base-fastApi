from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StrictStr, conint

from shared.utils.string_utils import to_camel


class PaginatedRequest(BaseModel):
    """Standard pagination request payload."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    items_per_page: conint(ge=1, le=100) = 20
    page: conint(ge=1) = 1
    search_params: StrictStr | None = Field(default=None, max_length=200)
    sort_by: StrictStr | None = Field(default=None, max_length=50)


__all__ = ["PaginatedRequest"]
