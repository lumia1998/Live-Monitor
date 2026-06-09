# -*- encoding: utf-8 -*-
"""
Extract live status and card metadata from spider data.
Stream URL resolution has been removed; this module handles
only live status detection and metadata field extraction.
"""
from __future__ import annotations

from .utils import trace_error_decorator

CARD_FIELD_KEYS = (
    "cover_url",
    "avatar_url",
    "viewer_count",
    "popularity",
    "like_count",
    "area_name",
    "started_at",
    "category",
)


def copy_card_fields(target: dict, source: dict) -> dict:
    for key in CARD_FIELD_KEYS:
        value = source.get(key)
        if value is not None and value != "":
            target[key] = value
    return target


def first_url(*values) -> str:
    if len(values) != 1:
        for item in values:
            url = first_url(item)
            if url:
                return url
        return ""
    value = values[0]
    if isinstance(value, str):
        return value if value.startswith(("http://", "https://", "data:image/")) else ""
    if isinstance(value, list):
        for item in value:
            url = first_url(item)
            if url:
                return url
    if isinstance(value, dict):
        for key in ("url", "uri", "web_uri"):
            url = first_url(value.get(key))
            if url:
                return url
        for key in ("url_list", "urls", "urlList"):
            url = first_url(value.get(key))
            if url:
                return url
    return ""


def first_value(*values):
    for value in values:
        if value is not None and value != "":
            return value
    return None


def extract_douyin_card_fields(json_data: dict) -> dict:
    owner = json_data.get("owner") or json_data.get("user") or {}
    stats = json_data.get("stats") or {}
    room_view_stats = json_data.get("room_view_stats") or {}
    cover_url = first_url(
        json_data.get("cover"),
        json_data.get("room_cover"),
        json_data.get("background"),
        json_data.get("dynamic_cover"),
        json_data.get("cover_uri"),
    )
    avatar_url = first_url(owner.get("avatar_thumb"), owner.get("avatar_medium"), owner.get("avatar_large"))
    user_count = first_value(
        json_data.get("user_count"),
        json_data.get("user_count_str"),
        stats.get("user_count"),
        stats.get("total_user_str"),
        room_view_stats.get("display_short"),
        room_view_stats.get("display_value"),
    )
    like_count = first_value(
        json_data.get("like_count"),
        json_data.get("digg_count"),
        stats.get("like_count"),
        stats.get("digg_count"),
    )
    fields = {
        "cover_url": cover_url,
        "avatar_url": avatar_url,
        "viewer_count": user_count if isinstance(user_count, int) else None,
        "popularity": user_count,
        "like_count": like_count,
        "started_at": first_value(json_data.get("create_time"), json_data.get("start_time")),
        "area_name": first_value(json_data.get("partition_name"), json_data.get("live_room_mode_name")),
    }
    return {key: value for key, value in fields.items() if value is not None and value != ""}


@trace_error_decorator
async def get_douyin_status(json_data: dict) -> dict:
    """Extract live status and metadata from Douyin spider data."""
    anchor_name = json_data.get("anchor_name")
    result: dict = {"anchor_name": anchor_name, "is_live": False}
    copy_card_fields(result, extract_douyin_card_fields(json_data))
    title = json_data.get("title", "")
    if title:
        result["title"] = title
    if json_data.get("status") == 2:
        result["is_live"] = True
    return result


@trace_error_decorator
async def get_tiktok_status(json_data: dict) -> dict:
    """Extract live status and metadata from TikTok spider data."""
    if not json_data:
        return {"anchor_name": None, "is_live": False}
    live_room_info = json_data["LiveRoom"]["liveRoomUserInfo"]
    user = live_room_info["user"]
    anchor_name = f"{user['nickname']}-{user['uniqueId']}"
    is_live = user.get("status") == 2
    result: dict = {"anchor_name": anchor_name, "is_live": is_live}
    if is_live:
        room = live_room_info["liveRoom"]
        result["title"] = room.get("title", "")
        result["cover_url"] = first_url(room.get("coverUrl"), room.get("cover"))
        result["viewer_count"] = room.get("viewerCount") or room.get("userCount")
    return result


@trace_error_decorator
async def get_kuaishou_status(json_data: dict) -> dict:
    """Extract live status and metadata from Kuaishou spider data."""
    result: dict = {
        "anchor_name": json_data.get("anchor_name"),
        "is_live": bool(json_data.get("is_live")),
    }
    if result["is_live"]:
        result["title"] = json_data.get("title", "")
    return copy_card_fields(result, json_data)


@trace_error_decorator
async def get_huya_status(json_data: dict) -> dict:
    """Extract live status and metadata from Huya spider data."""
    game_live_info = json_data["data"][0]["gameLiveInfo"]
    stream_info_list = json_data["data"][0]["gameStreamInfoList"]
    anchor_name = game_live_info.get("nick", "")
    is_live = bool(stream_info_list)
    result: dict = {"anchor_name": anchor_name, "is_live": is_live}
    if is_live:
        result["title"] = game_live_info.get("introduction", "")
        result["cover_url"] = game_live_info.get("screenshot", "")
        result["area_name"] = game_live_info.get("gameName", "")
        result["viewer_count"] = game_live_info.get("activityCount")
        result["avatar_url"] = game_live_info.get("avatar180", "") or game_live_info.get("avatar", "")
    return result


@trace_error_decorator
async def get_yy_status(json_data: dict) -> dict:
    """Extract live status from YY spider data."""
    is_live = "avp_info_res" in json_data
    result: dict = {
        "anchor_name": json_data.get("anchor_name", ""),
        "is_live": is_live,
    }
    if is_live:
        result["title"] = json_data.get("title", "")
    return result


@trace_error_decorator
async def get_bilibili_status(json_data: dict) -> dict:
    """Extract live status and metadata from Bilibili spider data."""
    is_live = bool(json_data.get("live_status"))
    result: dict = {
        "anchor_name": json_data.get("anchor_name"),
        "is_live": is_live,
    }
    if is_live:
        result["title"] = json_data.get("title", "")
    return copy_card_fields(result, json_data)


@trace_error_decorator
async def get_netease_status(json_data: dict) -> dict:
    """Extract live status and metadata from Netease CC spider data."""
    result: dict = {
        "anchor_name": json_data.get("anchor_name"),
        "is_live": bool(json_data.get("is_live")),
    }
    if result["is_live"]:
        result["title"] = json_data.get("title", "")
    return copy_card_fields(result, json_data)
