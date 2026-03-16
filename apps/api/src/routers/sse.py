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
