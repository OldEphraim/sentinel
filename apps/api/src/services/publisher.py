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
