import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionLocal, get_db
from src.models.order import Order
from src.models.watch import Watch
from src.schemas.watch import WatchCreateSchema as WatchCreateRequest
from src.services.agent import run_ordering_agent
from src.services.publisher import publish

router = APIRouter()


# --------------------------------------------------------------------------- #
# Serialization helpers
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
