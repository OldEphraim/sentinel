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
