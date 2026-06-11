# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from src.live_status import LiveStatus, LiveStatusResolver
from src.logger import logger
from src.monitor_config import ConfigStore, RoomSource, RuntimeSettings


@dataclass(slots=True)
class MonitorSnapshot:
    running: bool = False
    last_check_at: str = ""
    next_check_in: int = 0
    rooms: dict[str, LiveStatus] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self, include_stream_url: bool = False) -> dict[str, Any]:
        return {
            "running": self.running,
            "last_check_at": self.last_check_at,
            "next_check_in": self.next_check_in,
            "rooms": [room.to_dict(include_stream_url=include_stream_url) for room in self.rooms.values()],
            "errors": self.errors[-20:],
        }


class MonitorService:
    def __init__(self, config_store: ConfigStore | None = None) -> None:
        self.config_store = config_store or ConfigStore()
        self.settings: RuntimeSettings = self.config_store.load_runtime_settings()
        self.resolver = LiveStatusResolver(self.settings)
        self.snapshot = MonitorSnapshot()
        self._detected_live_started_at: dict[str, dt.datetime] = {}
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._check_lock = asyncio.Lock()

    def reload_settings(self) -> RuntimeSettings:
        self.settings = self.config_store.load_runtime_settings()
        self.resolver.refresh_settings(self.settings)
        return self.settings

    async def reload_settings_async(self) -> RuntimeSettings:
        self.settings = await asyncio.to_thread(self.config_store.load_runtime_settings)
        self.resolver.refresh_settings(self.settings)
        return self.settings

    def list_sources(self, include_disabled: bool = True) -> list[RoomSource]:
        return self.config_store.load_room_sources(include_disabled=include_disabled)

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self.snapshot.running = True
        self._task = asyncio.create_task(self._run_loop(), name="live-monitor-loop")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            await self._task
        self.snapshot.running = False

    async def _run_loop(self) -> None:
        logger.info("直播监控后台任务已启动")
        try:
            while not self._stop_event.is_set():
                try:
                    await self.check_all()
                except Exception as exc:
                    logger.error(f"直播监控循环异常: {exc}")
                    self.snapshot.errors.append(str(exc))

                wait_seconds = self.settings.check_interval
                for remaining in range(wait_seconds, 0, -1):
                    if self._stop_event.is_set():
                        break
                    self.snapshot.next_check_in = remaining
                    await asyncio.sleep(1)
        finally:
            self.snapshot.running = False
            logger.info("直播监控后台任务已停止")

    async def check_all(self) -> list[LiveStatus]:
        await self.reload_settings_async()
        sources = await asyncio.to_thread(self.list_sources, include_disabled=False)
        active_ids = {source.id for source in sources}
        for room_id in list(self.snapshot.rooms.keys()):
            if room_id not in active_ids:
                self.snapshot.rooms.pop(room_id, None)
        for room_id in list(self._detected_live_started_at.keys()):
            if room_id not in active_ids:
                self._detected_live_started_at.pop(room_id, None)
        return await self.check_sources(sources)

    async def check_room(self, source: RoomSource) -> LiveStatus:
        statuses = await self.check_sources([source])
        return statuses[0]

    async def check_sources(self, sources: Iterable[RoomSource]) -> list[LiveStatus]:
        sources = list(sources)
        statuses = await self.resolver.check_sources(sources) if sources else []
        async with self._check_lock:
            for status in statuses:
                self._apply_live_duration(status)
                # 关播时保留上一次开播状态的封面、头像、标题等画面数据
                if not status.is_live and not status.error:
                    cached = self.snapshot.rooms.get(status.id)
                    if cached and cached.is_live:
                        for field in ("cover_url", "avatar_url", "title", "anchor_name",
                                      "viewer_count", "popularity", "like_count",
                                      "area_name", "started_at", "category"):
                            cached_val = getattr(cached, field, None)
                            if cached_val and not getattr(status, field, None):
                                setattr(status, field, cached_val)
                self.snapshot.rooms[status.id] = status
                self._apply_status_updates(status)
            if statuses:
                self.snapshot.last_check_at = statuses[-1].checked_at
            self.snapshot.next_check_in = self.settings.check_interval
            return statuses


    def _apply_live_duration(self, status: LiveStatus) -> None:
        checked_at = parse_datetime(status.checked_at)

        if status.error:
            self._detected_live_started_at.pop(status.id, None)
            return

        if not status.is_live:
            self._detected_live_started_at.pop(status.id, None)
            status.detected_started_at = ""
            status.live_duration_seconds = None
            status.live_duration = ""
            return

        started_at = self._detected_live_started_at.get(status.id)
        if not started_at:
            started_at = checked_at
            self._detected_live_started_at[status.id] = started_at
        set_live_duration(status, started_at, checked_at)

    def _apply_status_updates(self, status: LiveStatus) -> None:
        new_cookies = status.extra.get("new_cookies")
        if new_cookies and status.platform == "SOOP":
            self.config_store.set_value("Cookie", "sooplive_cookie", new_cookies)
            self.settings.cookies["sooplive"] = new_cookies
        elif new_cookies and status.platform == "FlexTV":
            self.config_store.set_value("Cookie", "flextv_cookie", new_cookies)
            self.settings.cookies["flextv"] = new_cookies

        new_token = status.extra.get("new_token")
        if new_token and status.platform == "PopkonTV":
            self.config_store.set_value("Authorization", "popkontv_token", new_token)
            self.settings.authorization["popkontv_token"] = new_token

    def get_snapshot(self) -> MonitorSnapshot:
        return self.snapshot

    def get_cached_status(self, room_id: str) -> LiveStatus | None:
        return self.snapshot.rooms.get(room_id)

    def add_room(self, url: str, platform: str = "", name: str = "", enabled: bool = True) -> RoomSource:
        return self.config_store.add_room(url=url, platform=platform, name=name, enabled=enabled)

    def update_room(
        self,
        room_id: str,
        *,
        platform: str | None = None,
        name: str | None = None,
        enabled: bool | None = None,
    ) -> RoomSource | None:
        return self.config_store.update_room(room_id, platform=platform, name=name, enabled=enabled)

    def delete_room(self, room_id: str) -> RoomSource | None:
        deleted = self.config_store.delete_room(room_id)
        if deleted:
            self.snapshot.rooms.pop(room_id, None)
            self._detected_live_started_at.pop(room_id, None)
        return deleted


def parse_datetime(value: str) -> dt.datetime:
    if value:
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()
        except ValueError:
            pass
    return dt.datetime.now().astimezone()


def set_live_duration(status: LiveStatus, started_at: dt.datetime, checked_at: dt.datetime) -> None:
    seconds = max(0, int((checked_at - started_at).total_seconds()))
    status.detected_started_at = started_at.isoformat(timespec="seconds")
    status.live_duration_seconds = seconds
    status.live_duration = format_duration(seconds)


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return "不足1分钟"

    minutes = seconds // 60
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)

    if days:
        return f"{days}天{hours}小时{minutes}分钟"
    if hours:
        return f"{hours}小时{minutes}分钟"
    return f"{minutes}分钟"
