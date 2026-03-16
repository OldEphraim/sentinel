from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_watches() -> list:
    return []


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "router": "watches"}
