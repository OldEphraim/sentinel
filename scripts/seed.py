"""
Seed the Sentinel database with three demonstration watches.
Run with: python scripts/seed.py (from repo root, with API running)
"""
import asyncio
import httpx

API_BASE = "http://localhost:8000"

DEMO_WATCHES = [
    {
        "name": "Port of Rotterdam — Vessel Count",
        "question": "How many cargo vessels are currently anchored or docked in the Maasvlakte terminal?",
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [4.00, 51.93], [4.20, 51.93], [4.20, 52.02],
                [4.00, 52.02], [4.00, 51.93],
            ]],
        },
        "sensor_preference": "sar",   # SAR: North Sea is often cloudy
        "frequency": "daily",
        "alert_threshold": "fewer than 5 vessels",
    },
    {
        "name": "Permian Basin Drilling Activity",
        "question": "Are there active drilling rigs at this well pad? Has rig activity changed in the last 30 days?",
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [-102.10, 31.80], [-101.90, 31.80], [-101.90, 31.95],
                [-102.10, 31.95], [-102.10, 31.80],
            ]],
        },
        "sensor_preference": "optical",
        "frequency": "weekly",
        "alert_threshold": None,
    },
    {
        "name": "Lake Mead Water Level",
        "question": "Has the water surface area of Lake Mead changed significantly in the past 90 days?",
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [-114.80, 36.00], [-114.30, 36.00], [-114.30, 36.35],
                [-114.80, 36.35], [-114.80, 36.00],
            ]],
        },
        "sensor_preference": "free",   # Free Sentinel-2 is fine for reservoir extent
        "frequency": "monthly",
        "alert_threshold": "more than 10% change in water surface area",
    },
]


async def seed() -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        for watch_data in DEMO_WATCHES:
            try:
                resp = await client.post(f"{API_BASE}/api/watches/", json=watch_data)
                resp.raise_for_status()
                created = resp.json()
                print(f"✓ Created: {created['name']} (id: {created['id']})")
            except Exception as e:
                print(f"✗ Failed to create {watch_data['name']}: {e}")

    print("\nSeed complete. Visit http://localhost:3000")


if __name__ == "__main__":
    asyncio.run(seed())
