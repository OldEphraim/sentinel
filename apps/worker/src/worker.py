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

# Add the API src directory to path for local development.
# In Docker, all files are co-located in /app/src/ and python -m src.worker
# handles the path correctly — the conditional prevents a bad path insert.
_api_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../api")
if os.path.isdir(_api_root):
    sys.path.insert(0, _api_root)

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
