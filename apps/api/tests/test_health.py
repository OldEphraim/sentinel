"""Basic health check tests for the Sentinel API."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_health_returns_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_body():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "sentinel-api"


@pytest.mark.asyncio
async def test_mock_skyfi_search_archive():
    """Verify the mock SkyFi client returns realistic results."""
    from src.services.mock_skyfi import MockSkyFiClient

    mock = MockSkyFiClient()
    results = await mock.search_archive({}, "2024-01-01", "2024-12-31", None, False)
    assert len(results) >= 1
    for result in results:
        assert "id" in result
        assert "sensorType" in result
        assert result["sensorType"] in ("optical", "sar")
