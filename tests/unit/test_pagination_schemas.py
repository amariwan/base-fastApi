from __future__ import annotations

from shared.schemas.request.Pagination import PaginatedRequest
from shared.schemas.response.Pagination import PaginatedResponse


def test_paginated_request_defaults() -> None:
    req = PaginatedRequest()
    assert req.items_per_page == 20
    assert req.page == 1


def test_paginated_response_aliases() -> None:
    resp = PaginatedResponse[int](
        items_per_page=10,
        current_page=1,
        total_pages=1,
        total_count=1,
        skip_count=0,
        sort_by="-createdAt",
        items=[1, 2],
    )
    assert resp.items == [1, 2]
