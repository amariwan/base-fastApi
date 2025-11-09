from __future__ import annotations

import httpx
import pytest

from core.factory import create_app


@pytest.mark.asyncio
async def test_health_and_whoami_flow(hs_token) -> None:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/api/v1/health")
        assert health.status_code == 200

        token = hs_token({"roles": ["admin"]})
        whoami = await client.get(
            "/api/v1/whoami", headers={"Authorization": f"Bearer {token}"}
        )
        assert whoami.status_code == 200
        assert whoami.json()["roles"]
