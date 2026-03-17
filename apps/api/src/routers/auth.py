"""
Authentication endpoints: signup, login, me.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from geoalchemy2.shape import from_shape
from pydantic import BaseModel
from shapely.geometry import shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.models.user import User
from src.models.watch import Watch
from src.services.auth import create_token, get_current_user, hash_password, verify_password
from src.routers.watches import _trigger_watch_run

router = APIRouter()

# Same demo watches as scripts/seed.py
_DEMO_WATCHES = [
    {
        "name": "Port of Rotterdam — Vessel Count",
        "question": "How many cargo vessels are currently anchored or docked in the Maasvlakte terminal?",
        "aoi": {
            "type": "Polygon",
            "coordinates": [[[4.00, 51.93], [4.20, 51.93], [4.20, 52.02], [4.00, 52.02], [4.00, 51.93]]],
        },
        "sensor_preference": "sar",
        "frequency": "daily",
        "alert_threshold": "fewer than 5 vessels",
    },
    {
        "name": "Permian Basin Drilling Activity",
        "question": "Are there active drilling rigs at this well pad? Has rig activity changed in the last 30 days?",
        "aoi": {
            "type": "Polygon",
            "coordinates": [[[-102.10, 31.80], [-101.90, 31.80], [-101.90, 31.95], [-102.10, 31.95], [-102.10, 31.80]]],
        },
        "sensor_preference": "optical",
        "frequency": "weekly",
        "alert_threshold": None,
    },
    {
        "name": "Lake Mead Water Level",
        "question": "Has the water surface area of Lake Mead changed significantly in the past 90 days?",
        "aoi": {
            "type": "Polygon",
            "coordinates": [[[-114.80, 36.00], [-114.30, 36.00], [-114.30, 36.35], [-114.80, 36.35], [-114.80, 36.00]]],
        },
        "sensor_preference": "free",
        "frequency": "monthly",
        "alert_threshold": "more than 10% change in water surface area",
    },
]


class SignupRequest(BaseModel):
    email: str
    password: str
    demo_key: str


class LoginRequest(BaseModel):
    email: str
    password: str


def _user_dict(user: User) -> dict:
    return {"id": user.id, "email": user.email}


@router.post("/signup", status_code=201)
async def signup(
    body: SignupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if body.demo_key != settings.demo_key:
        raise HTTPException(status_code=403, detail="Invalid demo key")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        hashed_password=hash_password(body.password),
        created_at=datetime.utcnow(),
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    # Create the 3 demo watches for this user and schedule agent runs
    for demo in _DEMO_WATCHES:
        watch_id = str(uuid.uuid4())
        try:
            geom = from_shape(shape(demo["aoi"]), srid=4326)
            watch = Watch(
                id=watch_id,
                name=demo["name"],
                question=demo["question"],
                aoi=geom,
                sensor_preference=demo["sensor_preference"],
                frequency=demo["frequency"],
                alert_threshold=demo.get("alert_threshold"),
                user_id=user.id,
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(watch)
            await db.commit()
            background_tasks.add_task(
                _trigger_watch_run,
                watch_id=watch_id,
                question=demo["question"],
                aoi=demo["aoi"],
                sensor_preference=demo["sensor_preference"],
            )
        except Exception as e:
            print(f"[auth] Failed to create demo watch '{demo['name']}': {e}")

    token = create_token(user.id)
    return {"token": token, "user": _user_dict(user)}


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user.id)
    return {"token": token, "user": _user_dict(user)}


@router.get("/me")
async def me(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_dict(user)
