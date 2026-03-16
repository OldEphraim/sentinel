from pydantic import BaseModel
from typing import Optional


class OrderResponseSchema(BaseModel):
    id: str
    watch_id: str
    skyfi_order_id: Optional[str]
    status: str
    sensor_type: str
    analytics_type: Optional[str]
    cost_usd: Optional[float]
    created_at: str
    updated_at: str
    answer: Optional[str]
    confidence: Optional[str]
    evidence: Optional[list]
    captured_at: Optional[str]
    agent_thoughts: Optional[list]
