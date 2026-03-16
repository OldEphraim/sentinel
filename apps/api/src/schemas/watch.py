from pydantic import BaseModel
from typing import Optional


class WatchCreateSchema(BaseModel):
    name: str
    question: str
    aoi: dict
    sensor_preference: str = "auto"
    frequency: str = "once"
    alert_threshold: Optional[str] = None


class WatchResponseSchema(BaseModel):
    id: str
    name: str
    question: str
    aoi: dict
    sensor_preference: str
    frequency: str
    alert_threshold: Optional[str]
    status: str
    created_at: str
    updated_at: str
    last_run_at: Optional[str]
    next_run_at: Optional[str]
