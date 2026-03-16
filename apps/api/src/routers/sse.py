from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get("/watch/{watch_id}/orders")
async def watch_order_stream(watch_id: str) -> StreamingResponse:
    async def stub():
        yield "data: {}\n\n"
    return StreamingResponse(stub(), media_type="text/event-stream")
