"""
Client for the SkyFi Platform API.
API documentation: https://app.skyfi.com/platform-api/docs
Authentication: X-Skyfi-Api-Key header

When SKYFI_API_KEY is empty, all methods delegate to MockSkyFiClient.
"""
import httpx
from src.config import settings
from src.services.mock_skyfi import MockSkyFiClient


class SkyFiClient:
    def __init__(self) -> None:
        self._mock = MockSkyFiClient()
        self._headers = {
            "X-Skyfi-Api-Key": settings.skyfi_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _base(self) -> str:
        return settings.skyfi_api_base_url

    async def search_archive(
        self,
        aoi_geojson: dict,
        date_from: str,
        date_to: str,
        sensor_type: str | None = None,
        max_cloud_cover: int = 30,
        open_data_only: bool = False,
    ) -> list[dict]:
        if settings.use_mock_skyfi:
            return await self._mock.search_archive(aoi_geojson, date_from, date_to, sensor_type, open_data_only)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base()}/archive/search",
                headers=self._headers,
                json={
                    "aoi": aoi_geojson,
                    "dateRange": {"from": date_from, "to": date_to},
                    "sensorType": sensor_type,
                    "maxCloudCover": max_cloud_cover if sensor_type != "sar" else None,
                    "openData": open_data_only,
                },
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def place_archive_order(
        self,
        archive_id: str,
        analytics_type: str | None = None,
    ) -> dict:
        if settings.use_mock_skyfi:
            return await self._mock.place_archive_order(archive_id, analytics_type)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base()}/orders",
                headers=self._headers,
                json={"archiveId": archive_id, "analyticsType": analytics_type},
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def get_order_status(self, skyfi_order_id: str) -> dict:
        if settings.use_mock_skyfi:
            return await self._mock.get_order_status(skyfi_order_id)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self._base()}/orders/{skyfi_order_id}",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def get_analytics_products(self) -> list[dict]:
        if settings.use_mock_skyfi:
            return await self._mock.get_analytics_products()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{self._base()}/analytics/products", headers=self._headers)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def get_pass_predictions(self, aoi_geojson: dict, days_ahead: int = 7) -> list[dict]:
        if settings.use_mock_skyfi:
            return await self._mock.get_pass_predictions(aoi_geojson, days_ahead)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self._base()}/passes/predict",
                headers=self._headers,
                json={"aoi": aoi_geojson, "daysAhead": days_ahead},
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def estimate_cost(
        self,
        aoi_geojson: dict,
        sensor_type: str,
        analytics_type: str | None = None,
    ) -> dict:
        if settings.use_mock_skyfi:
            return await self._mock.estimate_cost(aoi_geojson, sensor_type, analytics_type)
        # Real API cost estimation endpoint (structure may vary — check docs)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self._base()}/orders/estimate",
                headers=self._headers,
                json={"sensorType": sensor_type, "analyticsType": analytics_type},
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]
