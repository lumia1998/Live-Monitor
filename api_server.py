# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.logger import logger
from src.monitor_config import RoomSource, normalize_url
from src.monitor_service import MonitorService


monitor_service = MonitorService()


class RoomCreate(BaseModel):
    url: str = Field(..., min_length=8)
    platform: str = ""
    name: str = ""
    enabled: bool = True


class RoomUpdate(BaseModel):
    platform: str | None = None
    name: str | None = None
    enabled: bool | None = None


class CheckRequest(BaseModel):
    url: str | None = None
    room_id: str | None = None
    platform: str = ""
    name: str = ""


class BatchCheckRequest(BaseModel):
    rooms: list[CheckRequest] = Field(default_factory=list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = await monitor_service.reload_settings_async()
    if settings.api.start_background_monitor:
        await monitor_service.start()
    yield
    await monitor_service.stop()


app = FastAPI(
    title="Live Monitor API",
    description="直播状态检测服务，不包含直播录制和通知推送功能。",
    version="1.0.2",
    lifespan=lifespan,
)


def require_api_token(authorization: str = Header(default=""), x_api_token: str = Header(default="")) -> None:
    settings = monitor_service.settings
    token = settings.api.token
    if not token:
        return
    bearer = ""
    if authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", maxsplit=1)[1].strip()
    if x_api_token == token or bearer == token:
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")


def source_from_check_request(payload: CheckRequest) -> RoomSource:
    if payload.room_id:
        source = monitor_service.config_store.find_room(payload.room_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Room not found: {payload.room_id}")
        return source
    if payload.url:
        return RoomSource(
            url=normalize_url(payload.url),
            platform=payload.platform,
            name=payload.name,
            enabled=True,
        )
    raise HTTPException(status_code=400, detail="Either room_id or url is required")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "running": monitor_service.get_snapshot().running}


@app.get("/api/status", dependencies=[Depends(require_api_token)])
def get_status(include_stream_url: bool = Query(default=False)) -> dict[str, Any]:
    settings = monitor_service.reload_settings()
    include_stream_url = include_stream_url or settings.include_stream_url
    return monitor_service.get_snapshot().to_dict(include_stream_url=include_stream_url)


@app.post("/api/check", dependencies=[Depends(require_api_token)])
async def check_once(payload: CheckRequest) -> dict[str, Any]:
    await monitor_service.reload_settings_async()
    if not payload.room_id and not payload.url:
        statuses = await monitor_service.check_all()
        return {
            "rooms": [status.to_dict(include_stream_url=monitor_service.settings.include_stream_url) for status in statuses]
        }

    source = source_from_check_request(payload)
    status_result = await monitor_service.check_room(source)
    return status_result.to_dict(include_stream_url=monitor_service.settings.include_stream_url)


@app.post("/api/check/batch", dependencies=[Depends(require_api_token)])
async def check_batch(payload: BatchCheckRequest) -> dict[str, Any]:
    await monitor_service.reload_settings_async()
    sources = []
    errors = []
    for i, room in enumerate(payload.rooms):
        try:
            source = source_from_check_request(room)
            sources.append(source)
        except HTTPException as e:
            errors.append(f"Room {i}: {e.detail}")
    
    if not sources:
        return {"rooms": [], "errors": errors}
    
    statuses = await monitor_service.check_sources(sources)
    return {
        "rooms": [status.to_dict(include_stream_url=monitor_service.settings.include_stream_url) for status in statuses],
        "errors": errors
    }


@app.get("/api/rooms", dependencies=[Depends(require_api_token)])
def list_rooms(include_disabled: bool = Query(default=True)) -> dict[str, Any]:
    rooms = monitor_service.list_sources(include_disabled=include_disabled)
    return {"rooms": [room.to_dict() for room in rooms]}


@app.post("/api/rooms", dependencies=[Depends(require_api_token)])
def add_room(payload: RoomCreate) -> dict[str, Any]:
    room = monitor_service.add_room(
        url=payload.url,
        platform=payload.platform,
        name=payload.name,
        enabled=payload.enabled,
    )
    return room.to_dict()


@app.patch("/api/rooms/{room_id}", dependencies=[Depends(require_api_token)])
def update_room(room_id: str, payload: RoomUpdate) -> dict[str, Any]:
    room = monitor_service.update_room(
        room_id,
        platform=payload.platform,
        name=payload.name,
        enabled=payload.enabled,
    )
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room.to_dict()


@app.delete("/api/rooms/{room_id}", dependencies=[Depends(require_api_token)])
def delete_room(room_id: str) -> dict[str, Any]:
    room = monitor_service.delete_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"deleted": room.to_dict()}


@app.post("/api/monitor/start", dependencies=[Depends(require_api_token)])
async def start_monitor() -> dict[str, Any]:
    await monitor_service.start()
    logger.info("通过 API 启动监控后台任务")
    return {"running": monitor_service.get_snapshot().running}


@app.post("/api/monitor/stop", dependencies=[Depends(require_api_token)])
async def stop_monitor() -> dict[str, Any]:
    await monitor_service.stop()
    logger.info("通过 API 停止监控后台任务")
    return {"running": monitor_service.get_snapshot().running}
