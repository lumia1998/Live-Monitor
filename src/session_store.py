# -*- coding: utf-8 -*-
"""直播场次记录（SQLite 持久化）。

场次记录存放在后端本地数据库，后端常驻运行、不随 Koishi 插件重启而丢失，
开播/关播状态由 MonitorService 的轮询状态机驱动写入。
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


class SessionStore:
    """基于 SQLite 的直播场次存储，线程安全（后端同步调用）。"""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS live_sessions (
                    id            TEXT PRIMARY KEY,
                    room_id       TEXT NOT NULL,
                    room_url      TEXT NOT NULL,
                    platform      TEXT NOT NULL DEFAULT '',
                    display_name  TEXT NOT NULL DEFAULT '',
                    avatar_url    TEXT NOT NULL DEFAULT '',
                    cover_url     TEXT NOT NULL DEFAULT '',
                    title         TEXT NOT NULL DEFAULT '',
                    started_at    TEXT NOT NULL,
                    ended_at      TEXT NOT NULL DEFAULT '',
                    completed     INTEGER NOT NULL DEFAULT 0,
                    duration_seconds INTEGER NOT NULL DEFAULT 0,
                    peak_viewer_count INTEGER NOT NULL DEFAULT 0,
                    final_like_count  INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_sessions_room ON live_sessions(room_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_sessions_started ON live_sessions(started_at)"
            )

    def list_sessions(
        self,
        room_id: str | None = None,
        include_incomplete: bool = True,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            sql = "SELECT * FROM live_sessions"
            clauses: list[str] = []
            params: list[Any] = []
            if room_id:
                clauses.append("room_id = ?")
                params.append(room_id)
            if not include_incomplete:
                clauses.append("completed = 1")
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY started_at ASC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def upsert_session(
        self,
        room_id: str,
        room_url: str,
        *,
        platform: str = "",
        display_name: str = "",
        avatar_url: str = "",
        cover_url: str = "",
        title: str = "",
        started_at: str | None = None,
        ended_at: str | None = None,
        completed: bool | None = None,
        duration_seconds: int = 0,
        peak_viewer_count: int = 0,
        final_like_count: int = 0,
    ) -> str:
        """插入或更新一场直播。返回场次 id。

        同 room 同 started_at 视为同一场次；调用方（MonitorService）负责
        在开播时插入（completed=0），关播时补 ended_at 并标记 completed=1。
        """
        started = started_at or _now_iso()
        session_id = f"{room_id}|{started}"
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM live_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE live_sessions SET
                        room_url = ?, platform = ?, display_name = ?,
                        avatar_url = ?, cover_url = ?, title = ?,
                        ended_at = ?, completed = ?, duration_seconds = ?,
                        peak_viewer_count = ?, final_like_count = ?
                    WHERE id = ?
                    """,
                    (
                        room_url,
                        platform,
                        display_name,
                        avatar_url,
                        cover_url,
                        title,
                        ended_at if ended_at is not None else existing["ended_at"],
                        1 if completed else existing["completed"],
                        duration_seconds,
                        peak_viewer_count,
                        final_like_count,
                        session_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO live_sessions (
                        id, room_id, room_url, platform, display_name,
                        avatar_url, cover_url, title, started_at, ended_at,
                        completed, duration_seconds, peak_viewer_count, final_like_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        room_id,
                        room_url,
                        platform,
                        display_name,
                        avatar_url,
                        cover_url,
                        title,
                        started,
                        ended_at or "",
                        1 if completed else 0,
                        duration_seconds,
                        peak_viewer_count,
                        final_like_count,
                    ),
                )
        return session_id

    def complete_open_sessions(self, room_id: str, ended_at: str | None = None) -> None:
        """把该房间所有未完成的场次标记为已完成（异常场景兜底）。"""
        ended = ended_at or _now_iso()
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM live_sessions WHERE room_id = ? AND completed = 0",
                (room_id,),
            ).fetchall()
            for row in rows:
                started = row["started_at"]
                duration = max(0, int(self._parse(started, ended)))
                conn.execute(
                    """
                    UPDATE live_sessions SET ended_at = ?, completed = 1, duration_seconds = ?
                    WHERE id = ?
                    """,
                    (ended, duration, row["id"]),
                )

    @staticmethod
    def _parse(started: str, ended: str) -> float:
        def to_ts(value: str) -> float:
            try:
                return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
            except ValueError:
                return dt.datetime.now().astimezone().timestamp()

        return to_ts(ended) - to_ts(started)
