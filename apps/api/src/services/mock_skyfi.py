"""
Mock implementation of the SkyFi Platform API for local development and demo.

Response shapes mirror the real SkyFi API as documented at:
https://app.skyfi.com/platform-api/docs

Order lifecycle simulation:
- Orders transition: pending → processing → complete after _ready_after timestamp
- Analytics results are generated deterministically based on analytics_type
- Delivery URLs are plausible-looking mock URLs
"""
import asyncio
import uuid
import random
from datetime import datetime, timedelta


class MockSkyFiClient:
    # Class-level order store so state persists across requests within a process
    _orders: dict[str, dict] = {}

    ANALYTICS_PRODUCTS: list[dict] = [
        {
            "id": "vehicle_detection",
            "name": "Vehicle Detection & Count",
            "description": "Detect and count cars, trucks, and heavy vehicles. Accuracy ~91%.",
            "pricePerSqKm": 5.0,
            "supportedSensors": ["optical"],
            "category": "object_detection",
        },
        {
            "id": "vessel_detection",
            "name": "Vessel Detection & Count",
            "description": "Detect and classify ships, tankers, and small vessels. Works on optical and SAR.",
            "pricePerSqKm": 6.0,
            "supportedSensors": ["optical", "sar"],
            "category": "object_detection",
        },
        {
            "id": "change_detection",
            "name": "Change Detection",
            "description": "Pixel-level change analysis between two images of the same area.",
            "pricePerSqKm": 4.0,
            "supportedSensors": ["optical", "sar"],
            "category": "change_detection",
        },
        {
            "id": "building_extraction",
            "name": "Building Footprint Extraction",
            "description": "Extract building footprints and estimate construction stage.",
            "pricePerSqKm": 7.0,
            "supportedSensors": ["optical"],
            "category": "object_detection",
        },
        {
            "id": "water_extent",
            "name": "Water Surface Extent",
            "description": "Measure water body surface area using NDWI (optical) or backscatter (SAR).",
            "pricePerSqKm": 3.0,
            "supportedSensors": ["optical", "sar"],
            "category": "material_detection",
        },
        {
            "id": "oil_tank_inventory",
            "name": "Oil Tank Inventory",
            "description": "Count oil storage tanks and estimate fill levels via shadow analysis.",
            "pricePerSqKm": 12.0,
            "supportedSensors": ["optical"],
            "category": "object_detection",
        },
    ]

    async def search_archive(
        self,
        aoi_geojson: dict,
        date_from: str,
        date_to: str,
        sensor_type: str | None,
        open_data_only: bool,
    ) -> list[dict]:
        await asyncio.sleep(0.3)
        results: list[dict] = []

        # Always include free Sentinel-2 unless SAR-only was requested
        if sensor_type != "sar":
            results.append({
                "id": f"s2_{uuid.uuid4().hex[:8]}",
                "provider": "Copernicus (ESA)",
                "satellite": "Sentinel-2B",
                "sensorType": "optical",
                "resolution": 10.0,
                "cloudCover": random.randint(0, 20),
                "capturedAt": (datetime.utcnow() - timedelta(days=random.randint(1, 5))).isoformat() + "Z",
                "thumbnailUrl": None,
                "price": 0.0,
                "openData": True,
                "bbox": [-74.02, 40.70, -73.97, 40.75],
            })

        if not open_data_only:
            if sensor_type in (None, "optical"):
                results.append({
                    "id": f"skysat_{uuid.uuid4().hex[:8]}",
                    "provider": "Planet",
                    "satellite": "SkySat-19",
                    "sensorType": "optical",
                    "resolution": 0.5,
                    "cloudCover": random.randint(0, 10),
                    "capturedAt": (datetime.utcnow() - timedelta(days=random.randint(0, 2))).isoformat() + "Z",
                    "thumbnailUrl": None,
                    "price": 25.0,
                    "openData": False,
                    "bbox": [-74.02, 40.70, -73.97, 40.75],
                })
                results.append({
                    "id": f"wv3_{uuid.uuid4().hex[:8]}",
                    "provider": "Vantor (Maxar)",
                    "satellite": "WorldView-3",
                    "sensorType": "optical",
                    "resolution": 0.3,
                    "cloudCover": random.randint(0, 5),
                    "capturedAt": (datetime.utcnow() - timedelta(days=random.randint(0, 1))).isoformat() + "Z",
                    "thumbnailUrl": None,
                    "price": 3250.0,
                    "openData": False,
                    "bbox": [-74.02, 40.70, -73.97, 40.75],
                })
            if sensor_type in (None, "sar"):
                results.append({
                    "id": f"iceye_{uuid.uuid4().hex[:8]}",
                    "provider": "ICEYE US",
                    "satellite": "ICEYE-X27",
                    "sensorType": "sar",
                    "resolution": 0.25,
                    "cloudCover": None,
                    "capturedAt": (datetime.utcnow() - timedelta(hours=random.randint(1, 12))).isoformat() + "Z",
                    "thumbnailUrl": None,
                    "price": 675.0,
                    "openData": False,
                    "bbox": [-74.02, 40.70, -73.97, 40.75],
                })
        return results

    async def place_archive_order(
        self,
        archive_id: str,
        analytics_type: str | None,
    ) -> dict:
        await asyncio.sleep(0.2)
        order_id = f"skyfi_ord_{uuid.uuid4().hex[:12]}"
        # Mock orders complete after 30 seconds to keep the demo snappy
        self._orders[order_id] = {
            "orderId": order_id,
            "archiveId": archive_id,
            "analyticsType": analytics_type,
            "status": "pending",
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "_ready_after": datetime.utcnow() + timedelta(seconds=30),
        }
        return {"orderId": order_id, "status": "pending"}

    async def place_tasking_order(
        self,
        aoi_geojson: dict,
        sensor_type: str,
    ) -> dict:
        await asyncio.sleep(0.2)
        order_id = f"skyfi_task_{uuid.uuid4().hex[:12]}"
        self._orders[order_id] = {
            "orderId": order_id,
            "status": "pending",
            "sensorType": sensor_type,
            "_ready_after": datetime.utcnow() + timedelta(seconds=60),
        }
        return {"orderId": order_id, "status": "pending"}

    async def get_order_status(self, skyfi_order_id: str) -> dict:
        await asyncio.sleep(0.1)
        if skyfi_order_id not in self._orders:
            return {"orderId": skyfi_order_id, "status": "not_found"}
        order = self._orders[skyfi_order_id]
        if datetime.utcnow() >= order["_ready_after"]:
            order["status"] = "complete"
            order["deliveryUrl"] = f"https://mock-delivery.skyfi.com/{skyfi_order_id}/imagery.zip"
            order["capturedAt"] = (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z"
            analytics_type = order.get("analyticsType")
            if analytics_type:
                order["analyticsResult"] = self._generate_analytics(analytics_type)
        elif order["status"] == "pending":
            order["status"] = "processing"
        return {k: v for k, v in order.items() if not k.startswith("_")}

    def _generate_analytics(self, analytics_type: str) -> dict:
        if analytics_type == "vehicle_detection":
            return {
                "detectedObjects": random.randint(12, 85),
                "objectType": "vehicle",
                "confidence": round(random.uniform(0.88, 0.95), 2),
                "breakdown": {"cars": random.randint(8, 50), "trucks": random.randint(2, 20), "heavy_equipment": random.randint(0, 10)},
            }
        if analytics_type == "vessel_detection":
            count = random.randint(3, 28)
            return {
                "detectedObjects": count,
                "objectType": "vessel",
                "confidence": round(random.uniform(0.85, 0.92), 2),
                "breakdown": {"cargo": random.randint(1, 15), "tanker": random.randint(0, 8), "small_craft": random.randint(0, 10)},
            }
        if analytics_type == "change_detection":
            pct = round(random.uniform(2.5, 22.0), 1)
            return {
                "changePercent": pct,
                "changeCategory": random.choice(["construction", "vegetation_loss", "new_structure"]),
                "confidence": round(random.uniform(0.82, 0.91), 2),
                "changedAreaSqM": round(pct * 1000, 0),
            }
        if analytics_type == "water_extent":
            area = round(random.uniform(4.2, 18.5), 2)
            change = round(random.uniform(-18.0, 3.0), 1)
            return {
                "waterAreaSqKm": area,
                "changeFromBaselinePct": change,
                "confidence": round(random.uniform(0.90, 0.96), 2),
                "method": "NDWI",
            }
        if analytics_type == "oil_tank_inventory":
            tanks = random.randint(8, 52)
            return {
                "tankCount": tanks,
                "estimatedAverageFillPct": random.randint(30, 85),
                "confidence": round(random.uniform(0.86, 0.93), 2),
            }
        if analytics_type == "building_extraction":
            return {
                "buildingCount": random.randint(15, 200),
                "newConstructionDetected": random.choice([True, False]),
                "confidence": round(random.uniform(0.88, 0.94), 2),
            }
        return {"rawResult": "complete", "confidence": 0.80}

    async def get_analytics_products(self) -> list[dict]:
        await asyncio.sleep(0.1)
        return self.ANALYTICS_PRODUCTS

    async def get_pass_predictions(self, aoi_geojson: dict, days_ahead: int = 7) -> list[dict]:
        await asyncio.sleep(0.1)
        predictions = []
        satellites = [
            ("Sentinel-2A", "Copernicus (ESA)", "optical", 10.0),
            ("ICEYE-X27", "ICEYE US", "sar", 0.25),
            ("SkySat-19", "Planet", "optical", 0.5),
            ("WorldView-3", "Vantor (Maxar)", "optical", 0.3),
        ]
        for i, (sat, provider, sensor, res) in enumerate(satellites):
            predictions.append({
                "satellite": sat,
                "provider": provider,
                "sensorType": sensor,
                "resolution": res,
                "predictedAt": (datetime.utcnow() + timedelta(hours=4 + i * 9)).isoformat() + "Z",
            })
        return predictions

    async def estimate_cost(
        self,
        aoi_geojson: dict,
        sensor_type: str,
        analytics_type: str | None,
    ) -> dict:
        imagery_cost = {"optical": 25.0, "sar": 675.0, "free": 0.0}.get(sensor_type, 25.0)
        analytics_cost = 0.0
        if analytics_type:
            for p in self.ANALYTICS_PRODUCTS:
                if p["id"] == analytics_type:
                    analytics_cost = p["pricePerSqKm"] * 5.0  # assume 5 sq km AOI
                    break
        return {
            "totalUsd": imagery_cost + analytics_cost,
            "imageryUsd": imagery_cost,
            "analyticsUsd": analytics_cost,
        }
