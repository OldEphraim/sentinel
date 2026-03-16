# STEPS.md — Sentinel Build Plan

Each step is self-contained. Read only the step you are currently executing. Do not read ahead. After completing a step and verifying it, update DECISION_LOG.md, then stop for human review.

---

## Step 1 — Initialize the monorepo structure

### What to create

Create every file and directory listed here. Exact contents are specified below.

```
sentinel/
├── DECISION_LOG.md
├── .env.example
├── .env                        (copy of .env.example, values filled in by human)
├── .gitignore
├── docker-compose.yml          (empty stub — just a comment for now)
├── pnpm-workspace.yaml
├── package.json
├── tsconfig.base.json
├── apps/
│   ├── web/.gitkeep
│   ├── api/.gitkeep
│   └── worker/.gitkeep
├── packages/
│   └── types/.gitkeep
├── scripts/.gitkeep
├── k8s/.gitkeep
└── helm/
    └── sentinel/.gitkeep
```

### File contents

**`.gitignore`:**
```
node_modules/
.next/
__pycache__/
*.pyc
.env
.venv/
dist/
build/
*.egg-info/
.DS_Store
*.log
.uv/
uv.lock
```

**`pnpm-workspace.yaml`:**
```yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

**`package.json`:**
```json
{
  "name": "sentinel",
  "private": true,
  "scripts": {
    "dev:web": "pnpm --filter @sentinel/web dev",
    "build:web": "pnpm --filter @sentinel/web build",
    "typecheck": "pnpm --filter @sentinel/web exec tsc --noEmit && pnpm --filter @sentinel/types exec tsc --noEmit"
  },
  "devDependencies": {
    "typescript": "^5.4.0"
  }
}
```

**`tsconfig.base.json`:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "skipLibCheck": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

**`.env.example`:**
```
# SkyFi Platform API
# Leave SKYFI_API_KEY empty to use the built-in mock (recommended for development)
SKYFI_API_KEY=
SKYFI_API_BASE_URL=https://app.skyfi.com/platform-api
SKYFI_WEBHOOK_SECRET=

# Anthropic — required even in mock mode (the agent still calls Claude)
ANTHROPIC_API_KEY=

# Postgres with PostGIS
DATABASE_URL=postgresql://sentinel:sentinel@localhost:5432/sentinel

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Frontend → API
NEXT_PUBLIC_API_URL=http://localhost:8000

# JWT signing key — generate with: openssl rand -hex 32
SECRET_KEY=
```

**`docker-compose.yml`** (stub for now):
```yaml
# Full docker-compose.yml is implemented in Step 13.
version: '3.9'
services: {}
```

**`DECISION_LOG.md`** — initial content:
```markdown
# Sentinel Decision Log

This file records non-trivial decisions made during development.
Append an entry at the end of every step.

---

## Step 1 — Monorepo scaffolding
**Decision:** Used pnpm workspaces monorepo with apps/ and packages/ separation.
**Alternatives considered:** Single flat repo; Turborepo; Nx.
**Reason:** pnpm workspaces is the lightest-weight option that still gives us workspace:* dependency linking between apps/web and packages/types. Turborepo/Nx add significant config overhead for a project of this size.
**Impact:** All Node packages are installed from the repo root with a single `pnpm install`. TypeScript path aliases between packages are handled by the workspace: protocol.
---
```

### Commands to run

```bash
pnpm install
```

Run from the repo root. Should complete without errors and create `node_modules/` at the root.

### Verification

- `ls` at the repo root shows all files listed in the structure above
- `pnpm install` completed without errors
- `DECISION_LOG.md` exists with the initial entry

### Stop here. Do not proceed to Step 2 until the human has reviewed.

---

## Step 2 — Shared types package (`packages/types`)

### What to create

```
packages/types/
├── package.json
├── tsconfig.json
└── src/
    ├── index.ts
    ├── watch.ts
    ├── order.ts
    ├── skyfi.ts
    └── agent.ts
```

### File contents

**`packages/types/package.json`:**
```json
{
  "name": "@sentinel/types",
  "version": "0.0.1",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  }
}
```

**`packages/types/tsconfig.json`:**
```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "noEmit": true
  },
  "include": ["src/**/*"]
}
```

**`packages/types/src/index.ts`:**
```typescript
export * from './watch';
export * from './order';
export * from './skyfi';
export * from './agent';
```

**`packages/types/src/watch.ts`:**
```typescript
export type SensorPreference = 'auto' | 'optical' | 'sar' | 'free';
export type WatchStatus = 'active' | 'paused' | 'error';
export type WatchFrequency = 'once' | 'daily' | 'weekly' | 'monthly';

export interface GeoJsonPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface WatchCreate {
  name: string;
  question: string;
  aoi: GeoJsonPolygon;
  sensor_preference: SensorPreference;
  frequency: WatchFrequency;
  alert_threshold?: string;
}

export interface Watch extends WatchCreate {
  id: string;
  created_at: string;
  updated_at: string;
  status: WatchStatus;
  last_run_at?: string;
  next_run_at?: string;
}
```

**`packages/types/src/order.ts`:**
```typescript
export type OrderStatus =
  | 'pending'
  | 'processing'
  | 'complete'
  | 'failed'
  | 'interpreting'
  | 'answered';

export interface EvidenceItem {
  type: 'count' | 'comparison' | 'detection' | 'measurement';
  description: string;
  value?: number | string;
}

export interface OrderResult {
  answer: string;
  confidence: 'high' | 'medium' | 'low';
  evidence: EvidenceItem[];
  rawAnalytics?: Record<string, unknown>;
  imageryUrl?: string;
  capturedAt?: string;
}

export interface Order {
  id: string;
  watchId: string;
  skyfiOrderId?: string;
  skyfiArchiveId?: string;
  status: OrderStatus;
  sensorType: string;
  analyticsType?: string;
  costUsd?: number;
  createdAt: string;
  updatedAt: string;
  result?: OrderResult;
  agentThoughts?: AgentThought[];
}
```

**`packages/types/src/skyfi.ts`:**
```typescript
export interface SkyFiArchiveResult {
  id: string;
  provider: string;
  satellite: string;
  sensorType: 'optical' | 'sar' | 'multispectral' | 'hyperspectral';
  resolution: number;
  cloudCover?: number;
  capturedAt: string;
  thumbnailUrl?: string;
  price: number;
  openData: boolean;
  bbox: [number, number, number, number];
}

export interface SkyFiOrderResponse {
  orderId: string;
  status: string;
  estimatedDelivery?: string;
}

export interface SkyFiAnalyticsProduct {
  id: string;
  name: string;
  description: string;
  pricePerSqKm: number;
  supportedSensors: string[];
  category: 'object_detection' | 'change_detection' | 'material_detection' | 'topographic';
}

export interface SkyFiPassPrediction {
  satellite: string;
  provider: string;
  predictedAt: string;
  resolution: number;
  sensorType: string;
}
```

**`packages/types/src/agent.ts`:**
```typescript
export interface AgentThought {
  step: number;
  toolCalled?: string;
  toolInput?: Record<string, unknown>;
  toolOutput?: Record<string, unknown>;
}

export interface AgentRun {
  watchId: string;
  orderId: string;
  thoughts: AgentThought[];
  finalAnswer?: string;
  error?: string;
}
```

Note: `AgentThought` is referenced by `Order` in `order.ts`. Because `agent.ts` is exported from `index.ts` alongside `order.ts`, this import is resolved through the barrel export — do NOT add an explicit import inside `order.ts`. The consumer (the frontend) gets everything from `@sentinel/types` and TypeScript resolves it.

### Commands to run

From the repo root:
```bash
pnpm install
pnpm exec tsc --noEmit -p packages/types/tsconfig.json
```

The typecheck must pass with zero errors.

### Verification

- Zero TypeScript errors from the typecheck command
- `packages/types/src/` contains all five files
- `DECISION_LOG.md` updated

### Stop here. Do not proceed to Step 3 until the human has reviewed.

---

## Step 3 — FastAPI backend scaffold (`apps/api`)

### What to create

Initialize the Python project and create the full directory skeleton with stub implementations that allow the app to start.

```
apps/api/
├── .python-version             (contains exactly: 3.11)
├── pyproject.toml
├── Dockerfile                  (stub — full content in Step 12)
└── src/
    ├── main.py
    ├── config.py
    ├── database.py
    ├── models/
    │   ├── __init__.py
    │   ├── watch.py
    │   └── order.py
    ├── schemas/
    │   ├── __init__.py
    │   ├── watch.py
    │   └── order.py
    ├── routers/
    │   ├── __init__.py
    │   ├── watches.py          (stub)
    │   ├── orders.py           (stub)
    │   ├── webhooks.py         (stub)
    │   └── sse.py              (stub)
    ├── services/
    │   ├── __init__.py
    │   ├── skyfi_client.py     (stub)
    │   ├── mock_skyfi.py       (stub)
    │   ├── agent.py            (stub)
    │   └── publisher.py        (stub)
    └── migrations/
        └── 001_initial.sql
```

### Initialization command

```bash
cd apps/api
uv init --name sentinel-api --python 3.11
```

This creates `pyproject.toml`. Then delete any `hello.py` or `main.py` that `uv init` generates, because we are creating our own.

### Dependencies — add with `uv add`

```bash
uv add fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg pydantic pydantic-settings \
       aio-pika anthropic httpx geoalchemy2 shapely alembic
```

### File contents

**`apps/api/src/config.py`:**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    skyfi_api_key: str = ""
    skyfi_api_base_url: str = "https://app.skyfi.com/platform-api"
    skyfi_webhook_secret: str = ""
    anthropic_api_key: str = ""
    database_url: str = "postgresql://sentinel:sentinel@localhost:5432/sentinel"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    secret_key: str = "dev-secret-change-in-production"

    @property
    def use_mock_skyfi(self) -> bool:
        return not self.skyfi_api_key


settings = Settings()
```

**`apps/api/src/database.py`:**
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from src.config import settings

# asyncpg requires postgresql+asyncpg:// scheme
_db_url = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
).replace(
    "postgresql+psycopg2://", "postgresql+asyncpg://"
)

engine = create_async_engine(_db_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        yield session
```

**`apps/api/src/models/watch.py`:**
```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry
from src.database import Base


class Watch(Base):
    __tablename__ = "watches"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    aoi: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    sensor_preference: Mapped[str] = mapped_column(String(50), nullable=False, default="auto")
    frequency: Mapped[str] = mapped_column(String(50), nullable=False, default="once")
    alert_threshold: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

**`apps/api/src/models/order.py`:**
```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    watch_id: Mapped[str] = mapped_column(String, nullable=False)
    skyfi_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    skyfi_archive_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    sensor_type: Mapped[str] = mapped_column(String(100), nullable=False)
    analytics_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_analytics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    imagery_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    agent_thoughts: Mapped[list | None] = mapped_column(JSON, nullable=True)
```

**`apps/api/src/migrations/001_initial.sql`:**
```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS watches (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    question TEXT NOT NULL,
    aoi GEOMETRY(POLYGON, 4326) NOT NULL,
    sensor_preference VARCHAR(50) NOT NULL DEFAULT 'auto',
    frequency VARCHAR(50) NOT NULL DEFAULT 'once',
    alert_threshold TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS watches_aoi_idx ON watches USING GIST(aoi);

CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR PRIMARY KEY,
    watch_id VARCHAR NOT NULL REFERENCES watches(id) ON DELETE CASCADE,
    skyfi_order_id VARCHAR,
    skyfi_archive_id VARCHAR,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    sensor_type VARCHAR(100) NOT NULL,
    analytics_type VARCHAR(100),
    cost_usd FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    answer TEXT,
    confidence VARCHAR(20),
    evidence JSONB,
    raw_analytics JSONB,
    imagery_url TEXT,
    captured_at TIMESTAMP,
    agent_thoughts JSONB
);

CREATE INDEX IF NOT EXISTS orders_watch_id_idx ON orders(watch_id);
CREATE INDEX IF NOT EXISTS orders_status_idx ON orders(status);
CREATE INDEX IF NOT EXISTS orders_skyfi_order_id_idx ON orders(skyfi_order_id);
```

**`apps/api/src/routers/__init__.py`:** (empty)

**`apps/api/src/routers/watches.py`** (stub):
```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_watches() -> list:
    return []


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "router": "watches"}
```

**`apps/api/src/routers/orders.py`** (stub):
```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/{order_id}")
async def get_order(order_id: str) -> dict:
    return {"id": order_id, "status": "stub"}
```

**`apps/api/src/routers/webhooks.py`** (stub):
```python
from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/skyfi")
async def skyfi_webhook(request: Request) -> dict:
    return {"received": True}
```

**`apps/api/src/routers/sse.py`** (stub):
```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get("/watch/{watch_id}/orders")
async def watch_order_stream(watch_id: str) -> StreamingResponse:
    async def stub():
        yield "data: {}\n\n"
    return StreamingResponse(stub(), media_type="text/event-stream")
```

**`apps/api/src/services/__init__.py`:** (empty)
**`apps/api/src/services/skyfi_client.py`** (stub):
```python
class SkyFiClient:
    pass
```

**`apps/api/src/services/mock_skyfi.py`** (stub):
```python
class MockSkyFiClient:
    pass
```

**`apps/api/src/services/agent.py`** (stub):
```python
async def run_ordering_agent(watch: dict) -> dict:
    return {"error": "not implemented"}


async def interpret_result(question: str, analytics_result: dict, sensor_type: str, captured_at: str | None) -> dict:
    return {"answer": "stub", "confidence": "low", "evidence": []}
```

**`apps/api/src/services/publisher.py`** (stub):
```python
async def publish(routing_key: str, message: dict) -> None:
    print(f"[publisher stub] {routing_key}: {message}")
```

**`apps/api/src/main.py`:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import watches, orders, webhooks, sse
from src.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Sentinel API",
    description="Autonomous Earth intelligence monitoring agent powered by SkyFi",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(watches.router, prefix="/api/watches", tags=["watches"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(sse.router, prefix="/api/sse", tags=["sse"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "sentinel-api"}
```

**`apps/api/Dockerfile`** (stub — will be replaced in Step 12):
```dockerfile
# Full Dockerfile implemented in Step 12
FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY . .
RUN uv sync
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Commands to run

Do NOT start the API yet — Postgres is not running. Just verify the Python imports are clean:

```bash
cd apps/api
uv run python -c "from src.main import app; print('imports ok')"
```

This must print `imports ok` with no errors. If there are import errors, fix them before proceeding.

### Verification

- `uv run python -c "from src.main import app; print('imports ok')"` prints `imports ok`
- All files listed in the structure exist
- `DECISION_LOG.md` updated

### Stop here. Do not proceed to Step 4 until the human has reviewed.

---

## Step 4 — Mock SkyFi client and real SkyFi client

This step implements the full `MockSkyFiClient` and `SkyFiClient`. The mock is the most critical piece of infrastructure for making the demo work without real credentials.

### `apps/api/src/services/mock_skyfi.py` — full implementation

```python
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
```

### `apps/api/src/services/skyfi_client.py` — full implementation

```python
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
```

### Verification

```bash
cd apps/api
uv run python -c "
import asyncio
from src.services.mock_skyfi import MockSkyFiClient

async def test():
    mock = MockSkyFiClient()
    results = await mock.search_archive({}, '2024-01-01', '2024-12-31', None, False)
    print(f'Archive search returned {len(results)} results')
    assert len(results) > 0
    order = await mock.place_archive_order(results[0]['id'], 'vehicle_detection')
    print(f'Order placed: {order[\"orderId\"]}')
    import asyncio
    await asyncio.sleep(0.5)
    status = await mock.get_order_status(order['orderId'])
    print(f'Order status: {status[\"status\"]}')
    products = await mock.get_analytics_products()
    print(f'Analytics products: {len(products)}')
    print('All mock tests passed')

asyncio.run(test())
"
```

All assertions must pass. Fix any errors before proceeding.

### Stop here. Do not proceed to Step 5 until the human has reviewed.

---

## Step 5 — AI agent implementation (`apps/api/src/services/agent.py`)

This is the core of the application. Replace the stub with the full implementation.

```python
"""
Claude tool-use agent for autonomous satellite imagery ordering.

The agent receives a watch (question + AOI + sensor preference) and:
1. Lists available analytics products
2. Searches the archive for suitable imagery
3. Estimates cost
4. Places the optimal order

The agent uses Claude's tool_use API feature — it reasons about which tools to
call and in what order, with no hardcoded decision logic.
"""
import json
from datetime import datetime, timedelta

import anthropic

from src.config import settings
from src.services.skyfi_client import SkyFiClient

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
_skyfi = SkyFiClient()

# --------------------------------------------------------------------------- #
# Tool definitions
# --------------------------------------------------------------------------- #

TOOLS: list[dict] = [
    {
        "name": "get_analytics_products",
        "description": (
            "List all available analytics products that can be applied to satellite imagery. "
            "Returns product IDs, descriptions, supported sensor types, and pricing. "
            "Always call this first so you know what analysis options are available."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_archive",
        "description": (
            "Search SkyFi's satellite image archive for imagery over an area of interest. "
            "Returns available images sorted by recency with resolution, price, cloud cover, and sensor type.\n\n"
            "SENSOR SELECTION RULES:\n"
            "- Maritime questions, vessel detection, cloudy regions → sensor_type='sar' (SAR works through clouds/night)\n"
            "- Vehicle counting, construction, visual change → sensor_type='optical'\n"
            "- Large area, low-budget, ~10m resolution acceptable → open_data_only=True (Sentinel-2, free)\n"
            "- If sensor_preference is 'auto', choose the best sensor for the question type\n\n"
            "For cloud-prone regions (North Sea, Pacific Northwest, tropics), prefer SAR even for visual questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "aoi_geojson": {
                    "type": "object",
                    "description": "GeoJSON Polygon geometry (pass the aoi exactly as provided)",
                },
                "date_from": {"type": "string", "description": "ISO 8601 date, e.g. 2024-01-01"},
                "date_to": {"type": "string", "description": "ISO 8601 date, e.g. 2024-12-31"},
                "sensor_type": {
                    "type": "string",
                    "enum": ["optical", "sar"],
                    "description": "Omit to search all sensor types",
                },
                "open_data_only": {
                    "type": "boolean",
                    "description": "If true, return only free Sentinel-2 open data",
                },
            },
            "required": ["aoi_geojson", "date_from", "date_to"],
        },
    },
    {
        "name": "estimate_cost",
        "description": (
            "Estimate the total cost (imagery + analytics) for an order before placing it. "
            "Always call this after selecting an image so the cost is logged."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "aoi_geojson": {"type": "object"},
                "sensor_type": {"type": "string", "enum": ["optical", "sar", "free"]},
                "analytics_type": {
                    "type": "string",
                    "description": "Analytics product ID (from get_analytics_products)",
                },
            },
            "required": ["aoi_geojson", "sensor_type"],
        },
    },
    {
        "name": "get_pass_predictions",
        "description": (
            "Get upcoming satellite pass predictions over the AOI. "
            "Call this if archive search returns no recent results, "
            "to tell the user when fresh imagery will be available."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "aoi_geojson": {"type": "object"},
                "days_ahead": {"type": "integer", "description": "How many days ahead to predict (default 7)"},
            },
            "required": ["aoi_geojson"],
        },
    },
    {
        "name": "place_order",
        "description": (
            "Place an order for a specific archive image with optional analytics. "
            "This is the final action — call it only after:\n"
            "1. Reviewing search results\n"
            "2. Selecting the best image for the question\n"
            "3. Estimating cost\n\n"
            "Choose analytics_type that best matches the question:\n"
            "- Counting vehicles/cars → vehicle_detection\n"
            "- Counting ships/vessels → vessel_detection\n"
            "- Construction/infrastructure change → change_detection\n"
            "- Water level/flood/reservoir → water_extent\n"
            "- Oil storage/commodity tracking → oil_tank_inventory\n"
            "- Building construction → building_extraction"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "archive_id": {
                    "type": "string",
                    "description": "The image ID from search_archive results",
                },
                "analytics_type": {
                    "type": "string",
                    "description": "Analytics product ID. Omit only if no analytics product matches.",
                },
                "sensor_type": {
                    "type": "string",
                    "description": "The sensor type of the selected image (for logging)",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explain why you chose this image and analytics product",
                },
            },
            "required": ["archive_id", "reasoning", "sensor_type"],
        },
    },
]

# --------------------------------------------------------------------------- #
# System prompts
# --------------------------------------------------------------------------- #

ORDERING_SYSTEM = """You are Sentinel's Earth intelligence agent. Your mission is to autonomously answer questions about locations on Earth by selecting and ordering the optimal satellite imagery and analytics from the SkyFi platform.

You will be given:
- A natural language question about a location
- The area of interest as a GeoJSON polygon
- A sensor preference (auto/optical/sar/free)
- A date range to search

Your job:
1. Call get_analytics_products to understand what analysis is available
2. Call search_archive to find suitable imagery (consider: recency, resolution, sensor appropriateness, cloud cover, cost)
3. Call estimate_cost for the chosen image + analytics combination
4. Call place_order with your chosen image ID, analytics type, and a clear reasoning statement

Be decisive. Do not ask clarifying questions. Make the best possible choice with available data.
You must always end by calling place_order — that is the success condition."""

INTERPRETATION_SYSTEM = """You are interpreting satellite imagery analytics results to answer a plain-English question about a location on Earth.

You will receive:
- The original question
- The sensor type and capture timestamp of the imagery
- The raw analytics output from SkyFi

Write a response that:
1. Directly and specifically answers the question
2. Cites the exact numeric evidence (counts, percentages, areas)
3. States the confidence level honestly
4. Notes relevant caveats (e.g., SAR cannot distinguish vehicle types; cloud cover may affect optical results)

Keep it to 2-4 sentences. Be direct. Do not hedge excessively.

Respond ONLY with valid JSON in this exact schema:
{
  "answer": "string — the plain-English answer",
  "confidence": "high" | "medium" | "low",
  "evidence": [
    {"type": "count" | "comparison" | "detection" | "measurement", "description": "string", "value": "string or number"}
  ]
}"""


# --------------------------------------------------------------------------- #
# Agent runner
# --------------------------------------------------------------------------- #

async def run_ordering_agent(watch: dict) -> dict:
    """
    Run the ordering agent for a watch.

    Args:
        watch: dict with keys: question, aoi (GeoJSON), sensor_preference

    Returns:
        dict with keys: skyfi_order_id, archive_id, sensor_type, analytics_type,
                        cost_usd, reasoning, agent_thoughts, error
    """
    today = datetime.utcnow().date().isoformat()
    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).date().isoformat()

    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"Question: {watch['question']}\n\n"
                f"Area of Interest (GeoJSON): {json.dumps(watch['aoi'])}\n"
                f"Sensor preference: {watch.get('sensor_preference', 'auto')}\n"
                f"Search date range: {thirty_days_ago} to {today}\n\n"
                "Please find the best satellite imagery and analytics to answer this question, "
                "then place the order."
            ),
        }
    ]

    result: dict = {
        "skyfi_order_id": None,
        "archive_id": None,
        "sensor_type": "optical",
        "analytics_type": None,
        "cost_usd": None,
        "reasoning": None,
        "agent_thoughts": [],
        "error": None,
    }

    for iteration in range(10):  # max 10 iterations
        try:
            response = await _client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=ORDERING_SYSTEM,
                tools=TOOLS,  # type: ignore[arg-type]
                messages=messages,
            )
        except Exception as e:
            result["error"] = f"Claude API error: {e}"
            break

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if not hasattr(block, "type") or block.type != "tool_use":
                continue

            tool_name: str = block.name
            tool_input: dict = block.input
            thought: dict = {
                "step": iteration,
                "toolCalled": tool_name,
                "toolInput": tool_input,
                "toolOutput": None,
            }

            try:
                if tool_name == "get_analytics_products":
                    output = await _skyfi.get_analytics_products()

                elif tool_name == "search_archive":
                    output = await _skyfi.search_archive(
                        aoi_geojson=tool_input["aoi_geojson"],
                        date_from=tool_input["date_from"],
                        date_to=tool_input["date_to"],
                        sensor_type=tool_input.get("sensor_type"),
                        open_data_only=tool_input.get("open_data_only", False),
                    )

                elif tool_name == "estimate_cost":
                    output = await _skyfi.estimate_cost(
                        aoi_geojson=tool_input["aoi_geojson"],
                        sensor_type=tool_input["sensor_type"],
                        analytics_type=tool_input.get("analytics_type"),
                    )
                    result["cost_usd"] = output.get("totalUsd")

                elif tool_name == "get_pass_predictions":
                    output = await _skyfi.get_pass_predictions(
                        aoi_geojson=tool_input["aoi_geojson"],
                        days_ahead=tool_input.get("days_ahead", 7),
                    )

                elif tool_name == "place_order":
                    order_resp = await _skyfi.place_archive_order(
                        archive_id=tool_input["archive_id"],
                        analytics_type=tool_input.get("analytics_type"),
                    )
                    result["skyfi_order_id"] = order_resp["orderId"]
                    result["archive_id"] = tool_input["archive_id"]
                    result["analytics_type"] = tool_input.get("analytics_type")
                    result["sensor_type"] = tool_input.get("sensor_type", "optical")
                    result["reasoning"] = tool_input.get("reasoning", "")
                    output = order_resp

                else:
                    output = {"error": f"Unknown tool: {tool_name}"}

                thought["toolOutput"] = output
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(output),
                })

            except Exception as e:
                error_output = {"error": str(e)}
                thought["toolOutput"] = error_output
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(error_output),
                    "is_error": True,
                })

            result["agent_thoughts"].append(thought)

        messages.append({"role": "user", "content": tool_results})

    if result["skyfi_order_id"] is None and result["error"] is None:
        result["error"] = "Agent completed without placing an order"

    return result


async def interpret_result(
    question: str,
    analytics_result: dict,
    sensor_type: str,
    captured_at: str | None,
) -> dict:
    """
    Use Claude to write a plain-English answer from raw SkyFi analytics output.

    Returns dict with: answer, confidence, evidence
    """
    prompt = (
        f"Question: {question}\n\n"
        f"Imagery: {sensor_type} sensor, captured {captured_at or 'recently'}\n\n"
        f"Analytics result:\n{json.dumps(analytics_result, indent=2)}"
    )
    try:
        response = await _client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=INTERPRETATION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text  # type: ignore[union-attr]
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
            raw = raw.rstrip("`").strip()
        return json.loads(raw)
    except Exception as e:
        return {
            "answer": f"Analytics processing complete. Raw result: {json.dumps(analytics_result)}",
            "confidence": "low",
            "evidence": [],
            "error": str(e),
        }
```

### Verification

```bash
cd apps/api
uv run python -c "
import asyncio
from src.services.agent import run_ordering_agent

async def test():
    result = await run_ordering_agent({
        'question': 'How many vessels are in this harbor?',
        'aoi': {'type': 'Polygon', 'coordinates': [[[4.0, 51.93],[4.2, 51.93],[4.2, 52.02],[4.0, 52.02],[4.0, 51.93]]]},
        'sensor_preference': 'sar',
    })
    print(f'Order ID: {result[\"skyfi_order_id\"]}')
    print(f'Sensor: {result[\"sensor_type\"]}')
    print(f'Analytics: {result[\"analytics_type\"]}')
    print(f'Thoughts: {len(result[\"agent_thoughts\"])} steps')
    print(f'Error: {result[\"error\"]}')
    assert result['skyfi_order_id'] is not None, 'Agent must place an order'
    print('Agent test passed')

asyncio.run(test())
"
```

The agent must place an order (non-null `skyfi_order_id`). If it fails, check that `ANTHROPIC_API_KEY` is set in `.env` and that `use_mock_skyfi` is True.

### Stop here. Do not proceed to Step 6 until the human has reviewed.

---

## Step 6 — RabbitMQ publisher

Replace the stub `apps/api/src/services/publisher.py`:

```python
"""
RabbitMQ message publisher.

Uses aio-pika for async AMQP. Each call opens a fresh connection —
acceptable for low-volume publishing. For high throughput, use a
connection pool (TODO for production).
"""
import json
import aio_pika
from src.config import settings


async def publish(routing_key: str, message: dict) -> None:
    """Publish a durable JSON message to a named queue."""
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url, timeout=10)
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue(routing_key, durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode("utf-8"),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=routing_key,
            )
            print(f"[publisher] Published to {routing_key}: {list(message.keys())}")
    except Exception as e:
        # Log but do not raise — a publish failure should not crash the API
        print(f"[publisher] ERROR publishing to {routing_key}: {e}")
```

Note: the publisher catches and logs exceptions rather than raising them. This is intentional — a RabbitMQ publish failure should not fail the HTTP request that triggered it. The watch will still be created; the worker will pick up the order when RabbitMQ recovers.

### Verification

No test for this step — RabbitMQ is not running locally yet (it starts in Docker Compose in Step 13). Just verify the file has no Python syntax errors:

```bash
cd apps/api
uv run python -c "from src.services.publisher import publish; print('publisher import ok')"
```

### Stop here. Do not proceed to Step 7 until the human has reviewed.

---

## Step 7 — Full FastAPI router implementations

This step replaces all four router stubs with complete implementations.

### `apps/api/src/routers/watches.py`

```python
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from geoalchemy2.shape import from_shape, to_shape
from pydantic import BaseModel
from shapely.geometry import shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionLocal, get_db
from src.models.order import Order
from src.models.watch import Watch
from src.services.agent import run_ordering_agent
from src.services.publisher import publish

router = APIRouter()


# --------------------------------------------------------------------------- #
# Pydantic schemas
# --------------------------------------------------------------------------- #

class WatchCreateRequest(BaseModel):
    name: str
    question: str
    aoi: dict  # GeoJSON Polygon
    sensor_preference: str = "auto"
    frequency: str = "once"
    alert_threshold: Optional[str] = None


# --------------------------------------------------------------------------- #
# Serialization helper
# --------------------------------------------------------------------------- #

def _serialize_watch(w: Watch) -> dict:
    geom = to_shape(w.aoi)
    coords = [list(c) for c in geom.exterior.coords]
    return {
        "id": w.id,
        "name": w.name,
        "question": w.question,
        "aoi": {"type": "Polygon", "coordinates": [coords]},
        "sensor_preference": w.sensor_preference,
        "frequency": w.frequency,
        "alert_threshold": w.alert_threshold,
        "status": w.status,
        "created_at": w.created_at.isoformat(),
        "updated_at": w.updated_at.isoformat(),
        "last_run_at": w.last_run_at.isoformat() if w.last_run_at else None,
        "next_run_at": w.next_run_at.isoformat() if w.next_run_at else None,
    }


def _serialize_order(o: Order) -> dict:
    return {
        "id": o.id,
        "watchId": o.watch_id,
        "skyfiOrderId": o.skyfi_order_id,
        "skyfiArchiveId": o.skyfi_archive_id,
        "status": o.status,
        "sensorType": o.sensor_type,
        "analyticsType": o.analytics_type,
        "costUsd": o.cost_usd,
        "createdAt": o.created_at.isoformat(),
        "updatedAt": o.updated_at.isoformat(),
        "answer": o.answer,
        "confidence": o.confidence,
        "evidence": o.evidence,
        "imageryUrl": o.imagery_url,
        "capturedAt": o.captured_at.isoformat() if o.captured_at else None,
        "agentThoughts": o.agent_thoughts,
    }


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@router.get("/")
async def list_watches(db: AsyncSession = Depends(get_db)) -> list:
    try:
        result = await db.execute(select(Watch).order_by(Watch.created_at.desc()))
        watches = result.scalars().all()
        return [_serialize_watch(w) for w in watches]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", status_code=201)
async def create_watch(
    body: WatchCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        geom = from_shape(shape(body.aoi), srid=4326)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid AOI geometry: {e}")

    watch = Watch(
        id=str(uuid.uuid4()),
        name=body.name,
        question=body.question,
        aoi=geom,
        sensor_preference=body.sensor_preference,
        frequency=body.frequency,
        alert_threshold=body.alert_threshold,
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    try:
        db.add(watch)
        await db.commit()
        await db.refresh(watch)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    # Fire-and-forget: run agent in background
    background_tasks.add_task(
        _trigger_watch_run,
        watch_id=watch.id,
        question=body.question,
        aoi=body.aoi,
        sensor_preference=body.sensor_preference,
    )
    return _serialize_watch(watch)


@router.get("/{watch_id}")
async def get_watch(watch_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    w = await db.get(Watch, watch_id)
    if not w:
        raise HTTPException(status_code=404, detail="Watch not found")
    return _serialize_watch(w)


@router.delete("/{watch_id}", status_code=204)
async def delete_watch(watch_id: str, db: AsyncSession = Depends(get_db)) -> None:
    w = await db.get(Watch, watch_id)
    if not w:
        raise HTTPException(status_code=404, detail="Watch not found")
    await db.delete(w)
    await db.commit()


@router.get("/{watch_id}/orders")
async def get_watch_orders(watch_id: str, db: AsyncSession = Depends(get_db)) -> list:
    result = await db.execute(
        select(Order)
        .where(Order.watch_id == watch_id)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    return [_serialize_order(o) for o in orders]


# --------------------------------------------------------------------------- #
# Background task
# --------------------------------------------------------------------------- #

async def _trigger_watch_run(
    watch_id: str,
    question: str,
    aoi: dict,
    sensor_preference: str,
) -> None:
    """
    Runs the agent, persists the Order record, and publishes to RabbitMQ.
    Runs as a FastAPI BackgroundTask — not in the HTTP request lifecycle.
    """
    print(f"[watches] Running agent for watch {watch_id}")
    try:
        agent_result = await run_ordering_agent({
            "question": question,
            "aoi": aoi,
            "sensor_preference": sensor_preference,
        })
    except Exception as e:
        print(f"[watches] Agent error for watch {watch_id}: {e}")
        agent_result = {"error": str(e), "skyfi_order_id": None, "sensor_type": "optical"}

    async with AsyncSessionLocal() as db:
        order = Order(
            id=str(uuid.uuid4()),
            watch_id=watch_id,
            skyfi_order_id=agent_result.get("skyfi_order_id"),
            skyfi_archive_id=agent_result.get("archive_id"),
            status="pending" if agent_result.get("skyfi_order_id") else "failed",
            sensor_type=agent_result.get("sensor_type", "optical"),
            analytics_type=agent_result.get("analytics_type"),
            cost_usd=agent_result.get("cost_usd"),
            agent_thoughts=agent_result.get("agent_thoughts"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(order)
        try:
            await db.commit()
        except Exception as e:
            print(f"[watches] DB error saving order for watch {watch_id}: {e}")
            return

        if order.skyfi_order_id:
            await publish("order.placed", {
                "orderId": order.id,
                "skyfiOrderId": order.skyfi_order_id,
                "watchId": watch_id,
                "analyticsType": order.analytics_type,
                "question": question,
                "sensorType": order.sensor_type,
            })
            print(f"[watches] Published order {order.id} to queue")
```

### `apps/api/src/routers/orders.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models.order import Order
from src.routers.watches import _serialize_order

router = APIRouter()


@router.get("/{order_id}")
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    o = await db.get(Order, order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return _serialize_order(o)
```

### `apps/api/src/routers/webhooks.py`

```python
"""
Webhook receiver for SkyFi order completion callbacks.

SkyFi sends a POST to this endpoint when an order's status changes.
We validate the HMAC signature (if configured) then publish to RabbitMQ.
"""
import hashlib
import hmac
import json

from fastapi import APIRouter, HTTPException, Request

from src.config import settings
from src.services.publisher import publish

router = APIRouter()


@router.post("/skyfi")
async def skyfi_webhook(request: Request) -> dict:
    body = await request.body()

    if settings.skyfi_webhook_secret:
        signature = request.headers.get("X-Skyfi-Signature", "")
        mac = hmac.new(
            settings.skyfi_webhook_secret.encode(),
            body,
            hashlib.sha256,
        )
        expected = f"sha256={mac.hexdigest()}"
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    order_id = payload.get("orderId")
    status = payload.get("status")

    if status == "complete" and order_id:
        await publish("order.ready", {
            "skyfiOrderId": order_id,
            "deliveryUrl": payload.get("deliveryUrl"),
            "analyticsResult": payload.get("analyticsResult"),
        })

    return {"received": True, "orderId": order_id, "status": status}
```

### `apps/api/src/routers/sse.py`

```python
"""
Server-Sent Events endpoint for real-time order status updates.

The frontend opens a persistent SSE connection when viewing a watch.
We poll the database every 3 seconds and push updates when status changes.
"""
import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.database import AsyncSessionLocal
from src.models.order import Order
from sqlalchemy import select

router = APIRouter()


@router.get("/watch/{watch_id}/orders")
async def watch_order_stream(watch_id: str) -> StreamingResponse:
    async def event_generator():
        last_seen: dict[str, str] = {}  # order_id → status
        consecutive_errors = 0

        while True:
            try:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Order)
                        .where(Order.watch_id == watch_id)
                        .order_by(Order.created_at.desc())
                        .limit(20)
                    )
                    orders = result.scalars().all()

                for o in orders:
                    if last_seen.get(o.id) != o.status:
                        last_seen[o.id] = o.status
                        data = json.dumps({
                            "orderId": o.id,
                            "status": o.status,
                            "answer": o.answer,
                            "confidence": o.confidence,
                            "evidence": o.evidence,
                            "agentThoughts": o.agent_thoughts,
                            "updatedAt": o.updated_at.isoformat(),
                        })
                        yield f"data: {data}\n\n"

                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                # Back off on repeated errors
                await asyncio.sleep(min(consecutive_errors * 3, 15))
                continue

            await asyncio.sleep(3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disables nginx buffering
        },
    )
```

### Verification

Start Postgres via Docker, then start the API:

```bash
docker run -d --name sentinel-pg \
  -e POSTGRES_USER=sentinel \
  -e POSTGRES_PASSWORD=sentinel \
  -e POSTGRES_DB=sentinel \
  -p 5432:5432 \
  postgis/postgis:15-3.3

cd apps/api
uv run uvicorn src.main:app --reload --port 8000
```

Then in a second terminal:
```bash
# Health check
curl http://localhost:8000/health

# Create a test watch
curl -s -X POST http://localhost:8000/api/watches/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Watch",
    "question": "How many vessels are in this area?",
    "aoi": {"type":"Polygon","coordinates":[[[4.0,51.93],[4.2,51.93],[4.2,52.02],[4.0,52.02],[4.0,51.93]]]},
    "sensor_preference": "sar"
  }' | python3 -m json.tool

# List watches
curl -s http://localhost:8000/api/watches/ | python3 -m json.tool
```

The watch creation must return a valid watch object with an `id`. Wait 5-10 seconds, then:
```bash
# Get orders for the watch (replace WATCH_ID)
curl -s http://localhost:8000/api/watches/WATCH_ID/orders | python3 -m json.tool
```

Should show an order in `pending` or `processing` status. Stop the Postgres container when done:
```bash
docker stop sentinel-pg && docker rm sentinel-pg
```

### Stop here. Do not proceed to Step 8 until the human has reviewed.

---

## Step 8 — Python worker service (`apps/worker`)

### Setup

```bash
cd apps/worker
uv init --name sentinel-worker --python 3.11
```

Add the `.python-version` file containing exactly `3.11`.

The worker reuses the API's models, config, and services by adding the API's `src/` to the Python path at runtime. This avoids duplicating code.

**Additional dependencies:**
```bash
uv add aio-pika sqlalchemy[asyncio] asyncpg pydantic-settings anthropic httpx geoalchemy2 shapely
```

### `apps/worker/src/worker.py`

```python
"""
Sentinel order worker.

Consumes from the 'order.placed' RabbitMQ queue.
For each message:
  1. Polls SkyFi until the order is complete (up to 10 minutes)
  2. Runs the interpretation agent on the analytics result
  3. Updates the Order record in Postgres with the answer
  4. Logs throughout

The worker must never crash on a bad message — all exceptions are caught per-message.
"""
import asyncio
import json
import os
import sys
from datetime import datetime

# Add the API src directory to path so we can reuse its models and services
_api_src = os.path.join(os.path.dirname(__file__), "../../api/src")
sys.path.insert(0, os.path.abspath(_api_src))

import aio_pika
from sqlalchemy import update

from src.config import settings
from src.database import AsyncSessionLocal
from src.models.order import Order
from src.services.agent import interpret_result
from src.services.skyfi_client import SkyFiClient

skyfi = SkyFiClient()

POLL_INTERVAL_SECONDS = 10
MAX_POLLS = 60  # 10 minutes total


async def handle_order_placed(message: aio_pika.IncomingMessage) -> None:
    async with message.process(requeue=False):
        try:
            payload = json.loads(message.body.decode("utf-8"))
        except Exception as e:
            print(f"[worker] Failed to parse message: {e}")
            return

        our_order_id: str = payload.get("orderId", "")
        skyfi_order_id: str = payload.get("skyfiOrderId", "")
        question: str = payload.get("question", "")
        analytics_type: str | None = payload.get("analyticsType")
        sensor_type: str = payload.get("sensorType", "optical")

        if not our_order_id or not skyfi_order_id:
            print(f"[worker] Invalid message — missing orderId or skyfiOrderId")
            return

        print(f"[worker] Processing order {our_order_id} (SkyFi: {skyfi_order_id})")

        for poll_num in range(MAX_POLLS):
            if poll_num > 0:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

            try:
                status_resp = await skyfi.get_order_status(skyfi_order_id)
            except Exception as e:
                print(f"[worker] Poll {poll_num + 1} error for {skyfi_order_id}: {e}")
                continue

            status = status_resp.get("status")
            print(f"[worker] Poll {poll_num + 1}/{MAX_POLLS}: {skyfi_order_id} → {status}")

            # Update order status in DB on every poll
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Order)
                    .where(Order.id == our_order_id)
                    .values(status="processing", updated_at=datetime.utcnow())
                )
                await db.commit()

            if status == "complete":
                analytics_result = status_resp.get("analyticsResult")
                delivery_url = status_resp.get("deliveryUrl")
                captured_at = status_resp.get("capturedAt")

                # Mark as interpreting
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(Order)
                        .where(Order.id == our_order_id)
                        .values(
                            status="interpreting",
                            imagery_url=delivery_url,
                            updated_at=datetime.utcnow(),
                        )
                    )
                    await db.commit()

                if analytics_result:
                    print(f"[worker] Interpreting analytics for order {our_order_id}")
                    try:
                        interpretation = await interpret_result(
                            question=question,
                            analytics_result=analytics_result,
                            sensor_type=sensor_type,
                            captured_at=captured_at,
                        )
                    except Exception as e:
                        print(f"[worker] Interpretation error for {our_order_id}: {e}")
                        interpretation = {
                            "answer": f"Imagery retrieved. Analytics: {json.dumps(analytics_result)}",
                            "confidence": "low",
                            "evidence": [],
                        }

                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            update(Order)
                            .where(Order.id == our_order_id)
                            .values(
                                status="answered",
                                answer=interpretation.get("answer"),
                                confidence=interpretation.get("confidence"),
                                evidence=interpretation.get("evidence"),
                                raw_analytics=analytics_result,
                                imagery_url=delivery_url,
                                captured_at=datetime.fromisoformat(captured_at.replace("Z", "+00:00")) if captured_at else None,
                                updated_at=datetime.utcnow(),
                            )
                        )
                        await db.commit()
                    print(f"[worker] Order {our_order_id} answered ✓")
                else:
                    # Complete but no analytics (raw imagery order)
                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            update(Order)
                            .where(Order.id == our_order_id)
                            .values(
                                status="complete",
                                imagery_url=delivery_url,
                                updated_at=datetime.utcnow(),
                            )
                        )
                        await db.commit()
                    print(f"[worker] Order {our_order_id} complete (no analytics)")
                return

            if status in ("failed", "cancelled", "not_found"):
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(Order)
                        .where(Order.id == our_order_id)
                        .values(status="failed", updated_at=datetime.utcnow())
                    )
                    await db.commit()
                print(f"[worker] Order {our_order_id} failed (SkyFi status: {status})")
                return

        # Timed out
        print(f"[worker] Order {our_order_id} timed out after {MAX_POLLS} polls")
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Order)
                .where(Order.id == our_order_id)
                .values(status="failed", updated_at=datetime.utcnow())
            )
            await db.commit()


async def main() -> None:
    print("[worker] Starting Sentinel worker...")
    print(f"[worker] Database: {settings.database_url[:40]}...")
    print(f"[worker] RabbitMQ: {settings.rabbitmq_url[:40]}...")
    print(f"[worker] SkyFi mock mode: {settings.use_mock_skyfi}")

    connection = await aio_pika.connect_robust(settings.rabbitmq_url, timeout=30)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=5)

    queue = await channel.declare_queue("order.placed", durable=True)
    await queue.consume(handle_order_placed)

    print("[worker] Listening on 'order.placed' queue...")
    try:
        await asyncio.Future()  # run forever
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### Verification

Cannot fully test until Docker Compose is running (Step 13). Verify no syntax errors:

```bash
cd apps/worker
uv run python -c "
import sys, os
sys.path.insert(0, os.path.abspath('../../api/src'))
from worker import main
print('worker imports ok')
" 2>&1 | head -20
```

Should print `worker imports ok`.

### Stop here. Do not proceed to Step 9 until the human has reviewed.

---

## Step 9 — Next.js frontend setup (`apps/web`)

### Initialization

```bash
cd apps/web
pnpm create next-app@latest . \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --no-turbo
```

Accept all defaults when prompted.

### Additional dependencies

```bash
pnpm add maplibre-gl react-map-gl @turf/turf lucide-react clsx
pnpm add -D @types/maplibre-gl
```

### Link the shared types package

In `apps/web/package.json`, add to `dependencies`:
```json
"@sentinel/types": "workspace:*"
```

Then from the repo root:
```bash
pnpm install
```

### Add MapLibre CSS to globals

In `apps/web/src/app/globals.css`, add after the Tailwind directives:
```css
@import 'maplibre-gl/dist/maplibre-gl.css';
```

### Utility files

**`apps/web/src/lib/api.ts`:**
```typescript
const API_BASE = process.env['NEXT_PUBLIC_API_URL'] ?? 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchWatches() {
  return apiFetch<unknown[]>('/api/watches/');
}

export async function fetchWatch(id: string) {
  return apiFetch<unknown>(`/api/watches/${id}`);
}

export async function fetchWatchOrders(watchId: string) {
  return apiFetch<unknown[]>(`/api/watches/${watchId}/orders`);
}

export async function createWatch(data: {
  name: string;
  question: string;
  aoi: object;
  sensor_preference: string;
  frequency: string;
  alert_threshold?: string;
}) {
  return apiFetch<unknown>('/api/watches/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteWatch(id: string) {
  return apiFetch<void>(`/api/watches/${id}`, { method: 'DELETE' });
}
```

**`apps/web/src/hooks/useOrderStream.ts`:**
```typescript
'use client';
import { useEffect, useState } from 'react';

const API_BASE = process.env['NEXT_PUBLIC_API_URL'] ?? 'http://localhost:8000';

export interface OrderUpdate {
  orderId: string;
  status: string;
  answer?: string;
  confidence?: string;
  evidence?: Array<{ type: string; description: string; value?: string | number }>;
  agentThoughts?: Array<{ step: number; toolCalled?: string; toolInput?: unknown; toolOutput?: unknown }>;
  updatedAt?: string;
}

export function useOrderStream(watchId: string): OrderUpdate[] {
  const [updates, setUpdates] = useState<OrderUpdate[]>([]);

  useEffect(() => {
    const source = new EventSource(`${API_BASE}/api/sse/watch/${watchId}/orders`);

    source.onmessage = (e: MessageEvent<string>) => {
      try {
        const data = JSON.parse(e.data) as OrderUpdate;
        if (!data.orderId) return;
        setUpdates((prev) => {
          const idx = prev.findIndex((u) => u.orderId === data.orderId);
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = data;
            return next;
          }
          return [data, ...prev];
        });
      } catch {
        // ignore parse errors
      }
    };

    source.onerror = () => {
      // SSE will auto-reconnect — no action needed
    };

    return () => source.close();
  }, [watchId]);

  return updates;
}
```

**`apps/web/src/lib/utils.ts`:**
```typescript
import { clsx, type ClassValue } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export const SENSOR_ICONS: Record<string, string> = {
  optical: '🌤',
  sar: '📡',
  free: '🌍',
};

export const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  processing: 'Processing',
  interpreting: 'Interpreting',
  answered: 'Answered',
  complete: 'Complete',
  failed: 'Failed',
};

export function statusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'text-slate-400',
    processing: 'text-blue-400',
    interpreting: 'text-violet-400',
    answered: 'text-emerald-400',
    complete: 'text-emerald-400',
    failed: 'text-red-400',
  };
  return colors[status] ?? 'text-slate-400';
}

export function statusBg(status: string): string {
  const colors: Record<string, string> = {
    pending: 'bg-slate-800 border-slate-600',
    processing: 'bg-blue-950 border-blue-700',
    interpreting: 'bg-violet-950 border-violet-700',
    answered: 'bg-emerald-950 border-emerald-700',
    complete: 'bg-emerald-950 border-emerald-700',
    failed: 'bg-red-950 border-red-800',
  };
  return colors[status] ?? 'bg-slate-800 border-slate-600';
}
```

### Verification

```bash
cd apps/web
pnpm dev
```

Should start without errors at http://localhost:3000. The default Next.js page is fine for now — we replace it in Step 10.

### Stop here. Do not proceed to Step 10 until the human has reviewed.

---

## Step 10 — Frontend pages and components

This step implements all frontend UI. Do these sub-steps in order.

### 10a — Layout

**`apps/web/src/app/layout.tsx`:**
```tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Link from 'next/link';
import { Satellite } from 'lucide-react';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Sentinel — Earth Intelligence',
  description: 'Autonomous satellite monitoring powered by SkyFi',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-100 min-h-screen`}>
        <nav className="border-b border-slate-800 px-6 py-4 flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 font-semibold text-lg hover:text-slate-300 transition-colors">
            <Satellite className="w-5 h-5 text-blue-400" />
            Sentinel
          </Link>
          <span className="text-slate-600 text-sm">Earth Intelligence powered by SkyFi</span>
          <div className="ml-auto">
            <Link
              href="/watches/new"
              className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              + New Watch
            </Link>
          </div>
        </nav>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
```

### 10b — Watch list page (`/`)

**`apps/web/src/app/page.tsx`:**
```tsx
'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { MapPin, Clock, Eye } from 'lucide-react';
import { fetchWatches } from '@/lib/api';
import { formatDate, SENSOR_ICONS, statusColor, statusBg } from '@/lib/utils';

export default function HomePage() {
  const [watches, setWatches] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const data = await fetchWatches();
      setWatches(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const interval = setInterval(() => void load(), 10_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-28 rounded-xl bg-slate-800 animate-pulse" />
        ))}
      </div>
    );
  }

  if (watches.length === 0) {
    return (
      <div className="text-center py-24">
        <div className="text-6xl mb-4">🛰️</div>
        <h2 className="text-2xl font-semibold mb-2">No watches yet</h2>
        <p className="text-slate-400 mb-8">
          Create a watch to start asking questions about any location on Earth.
        </p>
        <Link
          href="/watches/new"
          className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-lg font-medium transition-colors"
        >
          Create your first watch
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Active Watches</h1>
      <div className="space-y-3">
        {(watches as Record<string, unknown>[]).map((watch) => (
          <Link
            key={watch['id'] as string}
            href={`/watches/${watch['id'] as string}`}
            className="block"
          >
            <div className={`rounded-xl border p-5 hover:border-slate-500 transition-colors cursor-pointer ${statusBg('active')}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">
                      {SENSOR_ICONS[watch['sensor_preference'] as string] ?? '🛰️'}
                    </span>
                    <h3 className="font-medium truncate">{watch['name'] as string}</h3>
                  </div>
                  <p className="text-slate-400 text-sm line-clamp-2">{watch['question'] as string}</p>
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDate(watch['created_at'] as string)}
                  </span>
                  <span className="text-xs capitalize text-slate-400">
                    {watch['frequency'] as string}
                  </span>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

### 10c — Map component (polygon draw)

This is the most complex component. Create it as a separate client component.

**`apps/web/src/components/AoiMap.tsx`:**
```tsx
'use client';
import { useCallback, useRef, useState } from 'react';
import Map, { type MapRef, Source, Layer } from 'react-map-gl/maplibre';
import type { GeoJSONSourceRaw } from 'maplibre-gl';
import type { GeoJsonPolygon } from '@sentinel/types';

interface Props {
  value: GeoJsonPolygon | null;
  onChange: (polygon: GeoJsonPolygon | null) => void;
  readOnly?: boolean;
}

export default function AoiMap({ value, onChange, readOnly = false }: Props) {
  const mapRef = useRef<MapRef>(null);
  const [drawing, setDrawing] = useState(false);
  const [points, setPoints] = useState<[number, number][]>([]);

  const handleMapClick = useCallback(
    (e: { lngLat: { lng: number; lat: number } }) => {
      if (readOnly) return;
      const pt: [number, number] = [e.lngLat.lng, e.lngLat.lat];
      setDrawing(true);
      setPoints((prev) => [...prev, pt]);
    },
    [readOnly],
  );

  const handleDblClick = useCallback(
    (e: { lngLat: { lng: number; lat: number }; preventDefault: () => void }) => {
      if (readOnly || points.length < 3) return;
      e.preventDefault(); // prevent map zoom
      const closed: [number, number][] = [...points, points[0]!];
      const polygon: GeoJsonPolygon = {
        type: 'Polygon',
        coordinates: [closed],
      };
      onChange(polygon);
      setDrawing(false);
      setPoints([]);
    },
    [readOnly, points, onChange],
  );

  const clear = useCallback(() => {
    onChange(null);
    setDrawing(false);
    setPoints([]);
  }, [onChange]);

  // Build preview GeoJSON while drawing
  const previewGeoJson: GeoJSONSourceRaw = {
    type: 'geojson',
    data: {
      type: 'FeatureCollection',
      features:
        points.length >= 2
          ? [
              {
                type: 'Feature',
                properties: {},
                geometry: {
                  type: 'LineString',
                  coordinates: points,
                },
              },
            ]
          : [],
    },
  };

  const polygonGeoJson: GeoJSONSourceRaw = {
    type: 'geojson',
    data: value
      ? {
          type: 'Feature',
          properties: {},
          geometry: value,
        }
      : { type: 'FeatureCollection', features: [] },
  };

  return (
    <div className="relative w-full h-full rounded-lg overflow-hidden">
      <Map
        ref={mapRef}
        initialViewState={{ longitude: 0, latitude: 20, zoom: 1.5 }}
        style={{ width: '100%', height: '100%' }}
        mapStyle="https://demotiles.maplibre.org/style.json"
        onClick={handleMapClick}
        onDblClick={handleDblClick}
        cursor={readOnly ? 'default' : drawing ? 'crosshair' : 'pointer'}
        doubleClickZoom={false}
      >
        {/* Committed polygon */}
        <Source id="polygon" {...polygonGeoJson}>
          <Layer
            id="polygon-fill"
            type="fill"
            paint={{ 'fill-color': '#3b82f6', 'fill-opacity': 0.25 }}
          />
          <Layer
            id="polygon-outline"
            type="line"
            paint={{ 'line-color': '#3b82f6', 'line-width': 2 }}
          />
        </Source>

        {/* Drawing preview */}
        <Source id="preview" {...previewGeoJson}>
          <Layer
            id="preview-line"
            type="line"
            paint={{ 'line-color': '#f59e0b', 'line-width': 2, 'line-dasharray': [4, 2] }}
          />
        </Source>
      </Map>

      {/* Overlay instructions */}
      {!readOnly && (
        <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
          <div className="bg-slate-900/90 text-slate-300 text-xs px-3 py-1.5 rounded-md">
            {value
              ? '✓ AOI selected'
              : drawing && points.length >= 3
              ? 'Double-click to close polygon'
              : drawing
              ? `${points.length} points — click to add more`
              : 'Click to start drawing your area of interest'}
          </div>
          {(value ?? points.length > 0) && (
            <button
              type="button"
              onClick={clear}
              className="bg-red-900/80 hover:bg-red-800 text-red-200 text-xs px-3 py-1.5 rounded-md transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      )}
    </div>
  );
}
```

### 10d — New watch page (`/watches/new`)

**`apps/web/src/app/watches/new/page.tsx`:**
```tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import type { GeoJsonPolygon } from '@sentinel/types';
import { createWatch } from '@/lib/api';

// MapLibre must be dynamically imported (SSR would fail)
const AoiMap = dynamic(() => import('@/components/AoiMap'), { ssr: false });

const SENSOR_OPTIONS = [
  { value: 'auto', label: 'Auto — let the agent decide', icon: '🛰️' },
  { value: 'optical', label: 'Optical — visible light imagery', icon: '🌤' },
  { value: 'sar', label: 'SAR — radar, works through clouds', icon: '📡' },
  { value: 'free', label: 'Free — Sentinel-2 open data (10m)', icon: '🌍' },
];

const FREQUENCY_OPTIONS = [
  { value: 'once', label: 'Once' },
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
];

const EXAMPLE_QUESTIONS = [
  'How many cargo vessels are anchored here?',
  'Is there active construction at this site?',
  'Has the vegetation coverage changed in the last 30 days?',
  'How many vehicles are in this parking area?',
  'What is the current water extent of this reservoir?',
];

export default function NewWatchPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [question, setQuestion] = useState('');
  const [aoi, setAoi] = useState<GeoJsonPolygon | null>(null);
  const [sensorPreference, setSensorPreference] = useState('auto');
  const [frequency, setFrequency] = useState('once');
  const [alertThreshold, setAlertThreshold] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = name.trim() && question.trim() && aoi !== null && !submitting;

  const handleSubmit = async () => {
    if (!canSubmit || !aoi) return;
    setSubmitting(true);
    setError(null);
    try {
      const watch = await createWatch({
        name: name.trim(),
        question: question.trim(),
        aoi,
        sensor_preference: sensorPreference,
        frequency,
        alert_threshold: alertThreshold.trim() || undefined,
      }) as Record<string, unknown>;
      router.push(`/watches/${watch['id'] as string}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create watch');
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">New Watch</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Watch name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Port of Rotterdam vessel count"
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 placeholder:text-slate-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Question
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={3}
              placeholder="Ask anything about this location..."
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 placeholder:text-slate-500 resize-none"
            />
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => setQuestion(q)}
                  className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded px-2 py-1 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Sensor preference
            </label>
            <div className="space-y-2">
              {SENSOR_OPTIONS.map((opt) => (
                <label key={opt.value} className="flex items-center gap-3 cursor-pointer group">
                  <input
                    type="radio"
                    name="sensor"
                    value={opt.value}
                    checked={sensorPreference === opt.value}
                    onChange={() => setSensorPreference(opt.value)}
                    className="accent-blue-500"
                  />
                  <span className="text-lg">{opt.icon}</span>
                  <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                    {opt.label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Frequency
            </label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500"
            >
              {FREQUENCY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              Alert threshold{' '}
              <span className="text-slate-500 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              value={alertThreshold}
              onChange={(e) => setAlertThreshold(e.target.value)}
              placeholder='e.g. "fewer than 5 vessels" or "more than 20% change"'
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 placeholder:text-slate-500"
            />
          </div>

          {error && (
            <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-lg px-4 py-3">
              {error}
            </div>
          )}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium transition-colors"
          >
            {submitting ? 'Creating watch & running agent…' : 'Create Watch'}
          </button>

          {!aoi && (
            <p className="text-amber-500 text-xs text-center">
              ↗ Draw an area of interest on the map to continue
            </p>
          )}
        </div>

        {/* Map */}
        <div className="h-[500px] lg:h-full min-h-[400px]">
          <AoiMap value={aoi} onChange={setAoi} />
        </div>
      </div>
    </div>
  );
}
```

### 10e — Watch detail page (`/watches/[id]`)

**`apps/web/src/app/watches/[id]/page.tsx`:**
```tsx
'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import { ChevronDown, ChevronRight, Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { fetchWatch, fetchWatchOrders } from '@/lib/api';
import { useOrderStream } from '@/hooks/useOrderStream';
import { formatDate, SENSOR_ICONS, statusColor, statusBg, STATUS_LABELS } from '@/lib/utils';

const AoiMap = dynamic(() => import('@/components/AoiMap'), { ssr: false });

function StatusIcon({ status }: { status: string }) {
  if (['processing', 'interpreting', 'pending'].includes(status)) {
    return <Loader2 className="w-4 h-4 animate-spin text-blue-400" />;
  }
  if (status === 'answered' || status === 'complete') {
    return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
  }
  if (status === 'failed') {
    return <XCircle className="w-4 h-4 text-red-400" />;
  }
  return <Clock className="w-4 h-4 text-slate-400" />;
}

function OrderCard({ order }: { order: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);
  const status = order['status'] as string;
  const thoughts = order['agentThoughts'] as unknown[] | undefined;

  return (
    <div className={`rounded-xl border p-5 ${statusBg(status)}`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <StatusIcon status={status} />
          <span className={`text-sm font-medium ${statusColor(status)}`}>
            {STATUS_LABELS[status] ?? status}
          </span>
          {order['sensorType'] && (
            <span className="text-slate-500 text-xs">
              {SENSOR_ICONS[order['sensorType'] as string]} {order['sensorType'] as string}
            </span>
          )}
          {order['analyticsType'] && (
            <span className="text-slate-500 text-xs">• {order['analyticsType'] as string}</span>
          )}
        </div>
        <span className="text-xs text-slate-500">
          {formatDate(order['updatedAt'] as string ?? order['createdAt'] as string)}
        </span>
      </div>

      {/* Answer */}
      {order['answer'] && (
        <div className="bg-slate-900/60 rounded-lg p-4 mb-3">
          <p className="text-sm text-slate-100 leading-relaxed">{order['answer'] as string}</p>
          {order['confidence'] && (
            <p className="text-xs text-slate-500 mt-2">
              Confidence: <span className="capitalize">{order['confidence'] as string}</span>
            </p>
          )}
        </div>
      )}

      {/* Evidence */}
      {Array.isArray(order['evidence']) && order['evidence'].length > 0 && (
        <ul className="space-y-1 mb-3">
          {(order['evidence'] as Array<Record<string, unknown>>).map((item, i) => (
            <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
              <span className="text-slate-600 mt-0.5">•</span>
              <span>{item['description'] as string}{item['value'] !== undefined ? `: ${item['value']}` : ''}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Agent reasoning (collapsible) */}
      {thoughts && thoughts.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            Agent reasoning ({thoughts.length} steps)
          </button>
          {expanded && (
            <div className="mt-2 space-y-2">
              {(thoughts as Array<Record<string, unknown>>).map((t, i) => (
                <div key={i} className="bg-slate-900/40 rounded p-3 text-xs font-mono">
                  <div className="text-slate-400 mb-1">
                    Step {(t['step'] as number) + 1}: <span className="text-blue-400">{t['toolCalled'] as string}</span>
                  </div>
                  {t['toolInput'] && (
                    <pre className="text-slate-500 overflow-x-auto text-xs">
                      {JSON.stringify(t['toolInput'], null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function WatchDetailPage() {
  const params = useParams<{ id: string }>();
  const watchId = params.id;
  const [watch, setWatch] = useState<Record<string, unknown> | null>(null);
  const [orders, setOrders] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  const streamUpdates = useOrderStream(watchId);

  // Merge SSE updates into orders list
  useEffect(() => {
    if (streamUpdates.length === 0) return;
    setOrders((prev) => {
      const merged = [...prev];
      for (const update of streamUpdates) {
        const idx = merged.findIndex((o) => o['id'] === update.orderId);
        if (idx >= 0) {
          merged[idx] = { ...merged[idx], ...update, id: update.orderId };
        }
      }
      return [...merged];
    });
  }, [streamUpdates]);

  useEffect(() => {
    const load = async () => {
      try {
        const [w, o] = await Promise.all([
          fetchWatch(watchId) as Promise<Record<string, unknown>>,
          fetchWatchOrders(watchId) as Promise<Record<string, unknown>[]>,
        ]);
        setWatch(w);
        setOrders(o);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [watchId]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-12 bg-slate-800 rounded-xl animate-pulse w-1/2" />
        <div className="h-64 bg-slate-800 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (!watch) {
    return <div className="text-slate-400">Watch not found.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-2xl">{SENSOR_ICONS[watch['sensor_preference'] as string] ?? '🛰️'}</span>
          <h1 className="text-2xl font-semibold">{watch['name'] as string}</h1>
        </div>
        <p className="text-slate-400">{watch['question'] as string}</p>
        <p className="text-xs text-slate-600 mt-1">
          Created {formatDate(watch['created_at'] as string)} •{' '}
          {watch['frequency'] as string}
        </p>
      </div>

      {/* Map */}
      <div className="h-48 rounded-xl overflow-hidden border border-slate-700">
        <AoiMap
          value={watch['aoi'] as { type: 'Polygon'; coordinates: number[][][] } | null}
          onChange={() => {}}
          readOnly
        />
      </div>

      {/* Orders timeline */}
      <div>
        <h2 className="text-lg font-medium mb-3">Order History</h2>
        {orders.length === 0 ? (
          <div className="text-slate-500 text-sm flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Running agent...
          </div>
        ) : (
          <div className="space-y-3">
            {orders.map((order) => (
              <OrderCard key={order['id'] as string} order={order} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

### Verification

With the API running (`uv run uvicorn src.main:app --reload --port 8000` from `apps/api/`), start the frontend:

```bash
cd apps/web
pnpm dev
```

- http://localhost:3000 shows the watch list (empty state with CTA)
- http://localhost:3000/watches/new shows the two-column form + map
- Drawing a polygon on the map and clicking "Create Watch" creates a watch and redirects to the detail page
- The detail page shows the watch's question and AOI on the small map
- Fix all TypeScript errors reported by the dev server before proceeding

### Stop here. Do not proceed to Step 11 until the human has reviewed.

---

## Step 11 — Seed script

**`scripts/seed.py`:**

```python
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
```

### Verification

With the API running:
```bash
python scripts/seed.py
```

Should print three success lines. Then visit http://localhost:3000 and confirm the three watches appear.

### Stop here. Do not proceed to Step 12 until the human has reviewed.

---

## Step 12 — Dockerfiles

### `apps/api/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Install dependencies (before copying source — better layer caching)
COPY pyproject.toml ./
RUN uv sync --no-dev

# Copy source
COPY src/ ./src/

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `apps/worker/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

# Worker reuses the API's pyproject.toml for dependencies
COPY apps/api/pyproject.toml ./pyproject.toml
RUN uv sync --no-dev

# Copy API source (worker imports from it)
COPY apps/api/src/ ./src/

# Copy worker entrypoint
COPY apps/worker/src/worker.py ./src/worker.py

EXPOSE 8001
CMD ["uv", "run", "python", "src/worker.py"]
```

Note: The worker Dockerfile copies both `apps/api/src/` and `apps/worker/src/worker.py` into the same `src/` directory. This is intentional — the worker does `import src.config`, `src.database`, etc. which are the API's modules. The build context must be the repo root (see docker-compose.yml in Step 13).

### `apps/web/Dockerfile`

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
RUN npm install -g pnpm

# Copy workspace config
COPY pnpm-workspace.yaml package.json tsconfig.base.json ./

# Copy package.jsons for dependency installation
COPY packages/types/package.json ./packages/types/
COPY apps/web/package.json ./apps/web/

# Install all dependencies
RUN pnpm install --frozen-lockfile

# Copy source
COPY packages/types/ ./packages/types/
COPY apps/web/ ./apps/web/

# Build Next.js with standalone output
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @sentinel/web build

# Production image
FROM node:20-alpine

WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public

EXPOSE 3000
CMD ["node", "apps/web/server.js"]
```

Add this to `apps/web/next.config.ts` to enable standalone output:
```typescript
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
};

export default nextConfig;
```

### Verification

Build each image individually to check for errors:
```bash
# From repo root:
docker build -f apps/api/Dockerfile -t sentinel-api .
docker build -f apps/worker/Dockerfile -t sentinel-worker .
docker build -f apps/web/Dockerfile -t sentinel-web .
```

All three must build successfully. Fix any errors before proceeding.

### Stop here. Do not proceed to Step 13 until the human has reviewed.

---

## Step 13 — Docker Compose

Replace the stub `docker-compose.yml` with the full implementation:

```yaml
version: '3.9'

services:
  postgres:
    image: postgis/postgis:15-3.3
    restart: unless-stopped
    environment:
      POSTGRES_USER: sentinel
      POSTGRES_PASSWORD: sentinel
      POSTGRES_DB: sentinel
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./apps/api/src/migrations/001_initial.sql:/docker-entrypoint-initdb.d/001_initial.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sentinel -d sentinel"]
      interval: 5s
      timeout: 5s
      retries: 10

  rabbitmq:
    image: rabbitmq:3-management
    restart: unless-stopped
    ports:
      - "5672:5672"
      - "15672:15672"
    healthcheck:
      test: rabbitmq-diagnostics ping
      interval: 10s
      timeout: 5s
      retries: 10

  api:
    build:
      context: .
      dockerfile: apps/api/Dockerfile
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://sentinel:sentinel@postgres:5432/sentinel
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      SKYFI_API_KEY: ${SKYFI_API_KEY:-}
      SKYFI_API_BASE_URL: ${SKYFI_API_BASE_URL:-https://app.skyfi.com/platform-api}
      SKYFI_WEBHOOK_SECRET: ${SKYFI_WEBHOOK_SECRET:-}
      SECRET_KEY: ${SECRET_KEY:-dev-secret}
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy

  worker:
    build:
      context: .
      dockerfile: apps/worker/Dockerfile
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://sentinel:sentinel@postgres:5432/sentinel
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      SKYFI_API_KEY: ${SKYFI_API_KEY:-}
      SKYFI_WEBHOOK_SECRET: ${SKYFI_WEBHOOK_SECRET:-}
      SECRET_KEY: ${SECRET_KEY:-dev-secret}
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      api:
        condition: service_started

  web:
    build:
      context: .
      dockerfile: apps/web/Dockerfile
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - api

volumes:
  postgres_data:
```

Also create a `Makefile` at the repo root:
```makefile
.PHONY: up down build logs seed clean

up:
	docker compose up

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

seed:
	python scripts/seed.py

clean:
	docker compose down -v
	docker system prune -f
```

### Verification

```bash
docker compose up --build
```

Wait for all five services to be healthy. Then verify:
```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"sentinel-api"}

curl http://localhost:8000/api/watches/
# → []
```

RabbitMQ management UI should be accessible at http://localhost:15672 (user: guest, password: guest).

Frontend at http://localhost:3000 should load correctly.

Run the seed script:
```bash
python scripts/seed.py
```

Wait ~40 seconds, then check that the three watches have orders transitioning from `pending` → `processing` → `interpreting` → `answered`.

### Stop here. Do not proceed to Step 14 until the human has reviewed.

---

## Step 14 — Kubernetes manifests (`k8s/`)

Create the following files. They do not need to be deployed — they need to be valid YAML.

**`k8s/namespace.yaml`:**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: sentinel
```

**`k8s/secrets.yaml.example`:**
```yaml
# Copy to k8s/secrets.yaml, fill in values, NEVER COMMIT secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: sentinel-secrets
  namespace: sentinel
type: Opaque
stringData:
  ANTHROPIC_API_KEY: ""
  SKYFI_API_KEY: ""
  SKYFI_WEBHOOK_SECRET: ""
  DATABASE_URL: "postgresql://sentinel:CHANGE_ME@postgres:5432/sentinel"
  RABBITMQ_URL: "amqp://guest:guest@rabbitmq:5672/"
  SECRET_KEY: ""
```

Add `k8s/secrets.yaml` to `.gitignore`.

**`k8s/postgres.yaml`:** StatefulSet with 1 replica, postgis/postgis:15-3.3 image, PVC, ClusterIP Service.

**`k8s/rabbitmq.yaml`:** Deployment with 1 replica, rabbitmq:3-management, ClusterIP Service.

**`k8s/api.yaml`:** Deployment with 2 replicas, `gcr.io/YOUR_PROJECT/sentinel-api:latest`, env from secretRef `sentinel-secrets`, ClusterIP Service on port 8000.

**`k8s/worker.yaml`:** Deployment with 2 replicas, `gcr.io/YOUR_PROJECT/sentinel-worker:latest`, env from secretRef `sentinel-secrets`.

**`k8s/web.yaml`:** Deployment with 2 replicas, `gcr.io/YOUR_PROJECT/sentinel-web:latest`, LoadBalancer Service on port 80 → 3000.

**`k8s/ingress.yaml`:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sentinel-ingress
  namespace: sentinel
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
    - http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: sentinel-api
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: sentinel-web
                port:
                  number: 80
```

### Verification

```bash
# Validate all manifests (requires kubectl)
kubectl apply --dry-run=client -f k8s/
# OR if kubectl is not installed, just check YAML syntax:
python3 -c "
import yaml, glob
for f in glob.glob('k8s/*.yaml'):
    if 'secrets.yaml' in f: continue
    yaml.safe_load_all(open(f).read())
    print(f'✓ {f}')
"
```

All files must parse without YAML errors.

### Stop here. Do not proceed to Step 15 until the human has reviewed.

---

## Step 15 — Helm chart (`helm/sentinel/`)

```
helm/sentinel/
├── Chart.yaml
├── values.yaml
├── values.gke.yaml
├── values.eks.yaml
└── templates/
    ├── _helpers.tpl
    ├── namespace.yaml
    ├── postgres.yaml
    ├── rabbitmq.yaml
    ├── api.yaml
    ├── worker.yaml
    └── web.yaml
```

**`helm/sentinel/Chart.yaml`:**
```yaml
apiVersion: v2
name: sentinel
description: Autonomous Earth intelligence monitoring agent powered by SkyFi
type: application
version: 0.1.0
appVersion: "0.1.0"
keywords:
  - satellite
  - geospatial
  - skyfi
  - earth-observation
```

**`helm/sentinel/values.yaml`:**
```yaml
replicaCount:
  api: 2
  worker: 2
  web: 2

image:
  registry: gcr.io/YOUR_PROJECT
  tag: latest
  pullPolicy: IfNotPresent

resources:
  api:
    requests: { cpu: 250m, memory: 256Mi }
    limits:   { cpu: 500m, memory: 512Mi }
  worker:
    requests: { cpu: 250m, memory: 256Mi }
    limits:   { cpu: 500m, memory: 512Mi }
  web:
    requests: { cpu: 100m, memory: 128Mi }
    limits:   { cpu: 200m, memory: 256Mi }

postgresql:
  image: postgis/postgis:15-3.3
  storageClass: standard
  storageSize: 20Gi

rabbitmq:
  image: rabbitmq:3-management

service:
  web:
    type: LoadBalancer
    port: 80
```

**`helm/sentinel/values.gke.yaml`:**
```yaml
service:
  web:
    type: LoadBalancer
    annotations:
      cloud.google.com/load-balancer-type: "External"
postgresql:
  storageClass: standard-rwo
```

**`helm/sentinel/values.eks.yaml`:**
```yaml
service:
  web:
    type: LoadBalancer
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-type: nlb
postgresql:
  storageClass: gp2
```

**`helm/sentinel/templates/_helpers.tpl`:**
```
{{- define "sentinel.fullname" -}}
{{- printf "%s" .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
```

Templates for api.yaml, worker.yaml, web.yaml, postgres.yaml, rabbitmq.yaml, namespace.yaml — each should be a minimal but valid K8s manifest using `{{ .Values.* }}` for parameterized fields (replica counts, image tags, resource limits).

### Verification

```bash
helm lint helm/sentinel/
```

Must pass with no errors (warnings are acceptable).

### Stop here. Do not proceed to Step 16 until the human has reviewed.

---

## Step 16 — Integration test and CI

### Integration test

With `docker compose up` running and three demo watches seeded:

1. Visit http://localhost:3000 — all three watches visible
2. Click "Port of Rotterdam" — detail page loads, small AOI map renders
3. Wait 45 seconds — order should reach `answered` status with a vessel count answer
4. Verify the agent reasoning section is expandable and shows tool calls
5. Create a new watch from the UI — draw a polygon over any city, enter a question, submit
6. Confirm redirect to detail page and order beginning to process
7. RabbitMQ management at http://localhost:15672 → Queues tab shows `order.placed` with messages processed

### CI workflow

**`.github/workflows/ci.yml`:**
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm typecheck

  api-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          python-version: "3.11"
      - working-directory: apps/api
        run: uv sync
      - working-directory: apps/api
        run: uv run python -m pytest tests/ -v
        env:
          ANTHROPIC_API_KEY: "test-key"
          DATABASE_URL: "postgresql://x:x@localhost/x"
          RABBITMQ_URL: "amqp://guest:guest@localhost:5672/"
          SECRET_KEY: "test-secret"
```

**`apps/api/tests/__init__.py`:** (empty)

**`apps/api/tests/test_health.py`:**
```python
"""Basic smoke tests that don't require external services."""
import pytest
from src.config import Settings


def test_settings_defaults() -> None:
    """Settings should have sensible defaults when env vars are missing."""
    s = Settings(
        anthropic_api_key="test",
        database_url="postgresql://x:x@localhost/x",
        rabbitmq_url="amqp://x:x@localhost/",
        secret_key="test-secret",
    )
    assert s.use_mock_skyfi is True  # no SKYFI_API_KEY → mock mode
    assert s.skyfi_api_base_url == "https://app.skyfi.com/platform-api"


def test_mock_skyfi_is_default() -> None:
    """When SKYFI_API_KEY is empty, use_mock_skyfi must be True."""
    s = Settings(
        skyfi_api_key="",
        anthropic_api_key="test",
        database_url="postgresql://x:x@localhost/x",
        rabbitmq_url="amqp://x:x@localhost/",
        secret_key="test-secret",
    )
    assert s.use_mock_skyfi is True


@pytest.mark.asyncio
async def test_mock_search_returns_results() -> None:
    from src.services.mock_skyfi import MockSkyFiClient
    mock = MockSkyFiClient()
    results = await mock.search_archive({}, "2024-01-01", "2024-12-31", None, False)
    assert len(results) > 0
    assert all("id" in r for r in results)
    assert all("price" in r for r in results)
```

Add `pytest-asyncio` to dev dependencies:
```bash
cd apps/api
uv add --dev pytest pytest-asyncio
```

And add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Final verification checklist

- [ ] `docker compose up --build` starts cleanly from scratch
- [ ] `python scripts/seed.py` creates all three demo watches
- [ ] All three watches appear on the frontend
- [ ] At least one watch reaches `answered` status within 2 minutes
- [ ] The plain-English answer renders on the detail page
- [ ] Agent thoughts section is expandable
- [ ] Creating a watch from the UI works end-to-end
- [ ] `helm lint helm/sentinel/` passes
- [ ] `pnpm typecheck` passes from repo root
- [ ] `cd apps/api && uv run pytest tests/ -v` passes
- [ ] `.env` is gitignored
- [ ] `k8s/secrets.yaml` is gitignored (if it exists)

### Stop here. This is the final step. The project is complete when all checklist items pass.