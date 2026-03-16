from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/skyfi")
async def skyfi_webhook(request: Request) -> dict:
    return {"received": True}
