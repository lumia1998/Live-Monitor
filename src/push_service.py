# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import urllib.request
from typing import Any

from msg_push import bark, dingtalk, ntfy, pushplus, send_email, tg_bot, xizhi
from src.live_status import LiveStatus
from src.logger import logger
from src.monitor_config import PushSettings


DEFAULT_BEGIN_TEMPLATE = "直播间状态更新：[直播间名称] 正在直播中，时间：[时间]"
DEFAULT_OVER_TEMPLATE = "直播间状态更新：[直播间名称] 直播已结束，时间：[时间]"


class PushService:
    def __init__(self, settings: PushSettings) -> None:
        self.settings = settings

    def refresh_settings(self, settings: PushSettings) -> None:
        self.settings = settings

    def push_live_started(self, status: LiveStatus) -> dict[str, Any]:
        if not self.settings.begin_enabled:
            return {"success": [], "error": [], "skipped": True}
        content = render_template(self.settings.begin_template or DEFAULT_BEGIN_TEMPLATE, status)
        return self.push(status=status, event="live_started", content=content)

    def push_live_ended(self, status: LiveStatus) -> dict[str, Any]:
        if not self.settings.over_enabled:
            return {"success": [], "error": [], "skipped": True}
        content = render_template(self.settings.over_template or DEFAULT_OVER_TEMPLATE, status)
        return self.push(status=status, event="live_ended", content=content)

    def push(self, status: LiveStatus, event: str, content: str) -> dict[str, Any]:
        result = {"success": [], "error": []}
        channels = normalize_channels(self.settings.channels)
        if not channels:
            return result

        for channel in channels:
            try:
                channel_result = self._push_channel(channel, status, event, content)
                merge_result(result, channel, channel_result)
            except Exception as exc:
                logger.error(f"推送失败: channel={channel}, event={event}, error={exc}")
                result["error"].append({"channel": channel, "error": str(exc)})
        return result

    def _push_channel(self, channel: str, status: LiveStatus, event: str, content: str) -> dict[str, Any]:
        title = self.settings.title or "直播间状态更新通知"
        live_url = status.url

        if channel in {"钉钉", "dingtalk"}:
            return dingtalk(
                self.settings.dingtalk_url,
                content,
                self.settings.dingtalk_phone,
                self.settings.dingtalk_at_all,
            )
        if channel in {"微信", "xizhi", "息知"}:
            return xizhi(self.settings.wechat_url, title, content)
        if channel in {"tg", "telegram"}:
            return tg_bot(self.settings.tg_chat_id, self.settings.tg_token, content)
        if channel in {"邮箱", "email", "mail"}:
            return send_email(
                self.settings.email_host,
                self.settings.login_email,
                self.settings.email_password,
                self.settings.sender_email,
                self.settings.sender_name,
                self.settings.to_email,
                title,
                content,
                self.settings.smtp_port,
                self.settings.email_ssl,
            )
        if channel == "bark":
            return bark(
                self.settings.bark_url,
                title=title,
                content=content,
                level=self.settings.bark_level,
                sound=self.settings.bark_sound,
                url=live_url,
            )
        if channel == "ntfy":
            return ntfy(
                self.settings.ntfy_url,
                title=title,
                content=content,
                tags=self.settings.ntfy_tags,
                email=self.settings.ntfy_email,
                action_url=live_url,
            )
        if channel == "pushplus":
            return pushplus(self.settings.pushplus_token, title, content)
        if channel in {"webhook", "自定义webhook", "自定义Webhook"}:
            return send_webhook(self.settings.webhook_url, status, event, content, title)

        logger.warning(f"未知推送渠道，已跳过: {channel}")
        return {"success": [], "error": [channel]}


def render_template(template: str, status: LiveStatus) -> str:
    return (
        template.replace("[直播间名称]", status.display_name())
        .replace("[主播名称]", status.anchor_name or status.display_name())
        .replace("[平台]", status.platform)
        .replace("[标题]", status.title or "")
        .replace("[直播间地址]", status.url)
        .replace("[时间]", status.checked_at)
    ).replace(r"\n", "\n")


def normalize_channels(channels: list[str]) -> list[str]:
    normalized = []
    for channel in channels:
        item = channel.strip()
        if item:
            normalized.append(item.lower() if item.isascii() else item)
    return normalized


def merge_result(total: dict[str, Any], channel: str, channel_result: dict[str, Any]) -> None:
    if not isinstance(channel_result, dict):
        total["error"].append({"channel": channel, "error": str(channel_result)})
        return
    for key in ["success", "error"]:
        for item in channel_result.get(key, []):
            total[key].append({"channel": channel, "target": item})


def send_webhook(url: str, status: LiveStatus, event: str, content: str, title: str) -> dict[str, Any]:
    success = []
    error = []
    targets = [item.strip() for item in url.replace("，", ",").split(",") if item.strip()]
    if not targets:
        return {"success": success, "error": ["webhook_url_empty"]}

    payload = {
        "event": event,
        "title": title,
        "content": content,
        "room": status.to_dict(include_stream_url=True),
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    for target in targets:
        try:
            request = urllib.request.Request(target, data=data, headers=headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                if 200 <= response.status < 300:
                    success.append(target)
                else:
                    error.append(target)
        except Exception as exc:
            logger.error(f"自定义 webhook 推送失败: {target}, {exc}")
            error.append(target)
    return {"success": success, "error": error}
