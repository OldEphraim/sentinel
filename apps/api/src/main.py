from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import watches, orders, webhooks, sse
from src.routers import auth as auth_router
from src.database import engine, Base
import src.models.user  # noqa: F401 — registers User with Base.metadata


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

app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(watches.router, prefix="/api/watches", tags=["watches"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(sse.router, prefix="/api/sse", tags=["sse"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "sentinel-api"}
