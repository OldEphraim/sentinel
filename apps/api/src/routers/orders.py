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
