from fastapi import APIRouter

router = APIRouter()


@router.get("/{order_id}")
async def get_order(order_id: str) -> dict:
    return {"id": order_id, "status": "stub"}
