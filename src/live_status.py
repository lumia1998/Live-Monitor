# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import datetime as dt
import re
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from src import spider, stream, utils
from src.logger import logger
from src.monitor_config import RoomSource, RuntimeSettings


NAME_CLEAN_PATTERN = r"[\/\\\:\*\？?\"\<\>\|\&#.。,， ~！· ]"


@dataclass(slots=True)
class LiveStatus:
    id: str
    url: str
    platform: str
    is_live: bool
    anchor_name: str = ""
    configured_name: str = ""
    title: str = ""
    cover_url: str = ""
    avatar_url: str = ""
    viewer_count: Any = None
    popularity: Any = None
    like_count: Any = None
    area_name: str = ""
    started_at: str = ""
    detected_started_at: str = ""
    live_duration_seconds: int | None = None
    live_duration: str = ""
    category: str = ""
    checked_at: str = ""
    error: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def display_name(self) -> str:
        return self.configured_name or self.anchor_name or self.platform or self.url

    def to_dict(self, include_stream_url: bool = False) -> dict[str, Any]:
        # include_stream_url kept for API compatibility; stream URLs are no longer extracted
        return {
            "id": self.id,
            "url": self.url,
            "platform": self.platform,
            "is_live": self.is_live,
            "anchor_name": self.anchor_name,
            "configured_name": self.configured_name,
            "display_name": self.display_name(),
            "title": self.title,
            "cover_url": self.cover_url,
            "avatar_url": self.avatar_url,
            "viewer_count": self.viewer_count,
            "popularity": self.popularity,
            "like_count": self.like_count,
            "area_name": self.area_name,
            "started_at": self.started_at,
            "detected_started_at": self.detected_started_at,
            "live_duration_seconds": self.live_duration_seconds,
            "live_duration": self.live_duration,
            "category": self.category,
            "checked_at": self.checked_at,
            "error": self.error,
            **({"extra": self.extra} if self.extra else {}),
        }


class LiveStatusResolver:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)

    def refresh_settings(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)

    async def check_source(self, source: RoomSource) -> LiveStatus:
        async with self._semaphore:
            return await self._check_source(source)

    async def check_sources(self, sources: list[RoomSource]) -> list[LiveStatus]:
        return list(await asyncio.gather(*(self.check_source(source) for source in sources)))

    async def _check_source(self, source: RoomSource) -> LiveStatus:
        checked_at = now_iso()
        platform = "未知平台"
        try:
            port_info: dict[str, Any] = {}
            url = source.url
            hostname = urlparse(url).hostname or ""

            if "douyin.com" in hostname:
                platform = "抖音直播"
                if "v.douyin.com" not in url and "/user/" not in url:
                    json_data = await spider.get_douyin_web_stream_data(
                        url=url, cookies=self.cookie("douyin")
                    )
                else:
                    json_data = await spider.get_douyin_app_stream_data(
                        url=url, cookies=self.cookie("douyin")
                    )
                port_info = await stream.get_douyin_status(json_data)

            elif "tiktok.com" in hostname:
                platform = "TikTok直播"
                json_data = await spider.get_tiktok_stream_data(
                    url=url, cookies=self.cookie("tiktok")
                )
                port_info = await stream.get_tiktok_status(json_data)

            elif "kuaishou.com" in hostname:
                platform = "快手直播"
                json_data = await spider.get_kuaishou_stream_data(
                    url=url, cookies=self.cookie("kuaishou")
                )
                port_info = await stream.get_kuaishou_status(json_data)

            elif "huya.com" in hostname:
                platform = "虎牙直播"
                json_data = await spider.get_huya_stream_data(
                    url=url, cookies=self.cookie("huya")
                )
                port_info = await stream.get_huya_status(json_data)

            elif "douyu.com" in hostname:
                platform = "斗鱼直播"
                port_info = await spider.get_douyu_info_data(
                    url=url, cookies=self.cookie("douyu")
                )

            elif "yy.com" in hostname:
                platform = "YY直播"
                json_data = await spider.get_yy_stream_data(
                    url=url, cookies=self.cookie("yy")
                )
                port_info = await stream.get_yy_status(json_data)

            elif "bilibili.com" in hostname:
                platform = "B站直播"
                json_data = await spider.get_bilibili_room_info(
                    url=url, cookies=self.cookie("bilibili")
                )
                port_info = await stream.get_bilibili_status(json_data)

            elif "xhslink.com" in hostname or "xiaohongshu.com" in hostname:
                platform = "小红书直播"
                port_info = await spider.get_xhs_stream_url(
                    url, cookies=self.cookie("xhs")
                )

            elif "bigo.tv" in hostname or "bigovideo.tv" in hostname:
                platform = "Bigo直播"
                port_info = await spider.get_bigo_stream_url(
                    url, cookies=self.cookie("bigo")
                )

            elif "blued.cn" in hostname:
                platform = "Blued直播"
                port_info = await spider.get_blued_stream_url(
                    url, cookies=self.cookie("blued")
                )

            elif "sooplive.co.kr" in hostname or "sooplive.com" in hostname:
                platform = "SOOP"
                port_info = await spider.get_sooplive_stream_data(
                    url=url,
                    cookies=self.cookie("sooplive"),
                    username=self.account("sooplive_username"),
                    password=self.account("sooplive_password"),
                )

            elif "cc.163.com" in hostname:
                platform = "网易CC直播"
                json_data = await spider.get_netease_stream_data(url=url, cookies=self.cookie("netease"))
                port_info = await stream.get_netease_status(json_data)

            elif "qiandurebo.com" in hostname:
                platform = "千度热播"
                port_info = await spider.get_qiandurebo_stream_data(
                    url=url, cookies=self.cookie("qiandurebo")
                )

            elif "pandalive.co.kr" in hostname:
                platform = "PandaTV"
                port_info = await spider.get_pandatv_stream_data(
                    url=url, cookies=self.cookie("pandatv")
                )

            elif "missevan.com" in hostname:
                platform = "猫耳FM直播"
                port_info = await spider.get_maoerfm_stream_url(
                    url=url, cookies=self.cookie("maoerfm")
                )

            elif "winktv.co.kr" in hostname:
                platform = "WinkTV"
                port_info = await spider.get_winktv_stream_data(
                    url=url, cookies=self.cookie("winktv")
                )

            elif "flextv.co.kr" in hostname or "ttinglive.com" in hostname:
                platform = "FlexTV"
                json_data = await spider.get_flextv_stream_data(
                    url=url,
                    cookies=self.cookie("flextv"),
                    username=self.account("flextv_username"),
                    password=self.account("flextv_password"),
                )
                port_info = ensure_dict(json_data)

            elif "look.163.com" in hostname:
                platform = "Look直播"
                port_info = await spider.get_looklive_stream_url(
                    url=url, cookies=self.cookie("look")
                )

            elif "popkontv.com" in hostname:
                platform = "PopkonTV"
                port_info = await spider.get_popkontv_stream_url(
                    url=url,
                    access_token=self.settings.authorization.get("popkontv_token", ""),
                    username=self.account("popkontv_username"),
                    password=self.account("popkontv_password"),
                    partner_code=self.account("popkontv_partner_code"),
                )

            elif "twitcasting.tv" in hostname:
                platform = "TwitCasting"
                port_info = await spider.get_twitcasting_stream_url(
                    url=url,
                    cookies=self.cookie("twitcasting"),
                    account_type=self.account("twitcasting_account_type"),
                    username=self.account("twitcasting_username"),
                    password=self.account("twitcasting_password"),
                )

            elif "baidu.com" in hostname:
                platform = "百度直播"
                port_info = await spider.get_baidu_stream_data(
                    url=url, cookies=self.cookie("baidu")
                )

            elif "weibo.com" in hostname:
                platform = "微博直播"
                port_info = await spider.get_weibo_stream_data(
                    url=url, cookies=self.cookie("weibo")
                )

            elif "kugou.com" in hostname:
                platform = "酷狗直播"
                port_info = await spider.get_kugou_stream_url(
                    url=url, cookies=self.cookie("kugou")
                )

            elif "twitch.tv" in hostname:
                platform = "TwitchTV"
                port_info = await spider.get_twitchtv_stream_data(
                    url=url, cookies=self.cookie("twitch")
                )

            elif "liveme.com" in hostname:
                platform = "LiveMe"
                port_info = await spider.get_liveme_stream_url(
                    url=url, cookies=self.cookie("liveme")
                )

            elif "huajiao.com" in hostname:
                platform = "花椒直播"
                port_info = await spider.get_huajiao_stream_url(
                    url=url, cookies=self.cookie("huajiao")
                )

            elif "7u66.com" in hostname:
                platform = "流星直播"
                port_info = await spider.get_liuxing_stream_url(
                    url=url, cookies=self.cookie("liuxing")
                )

            elif "showroom-live.com" in hostname:
                platform = "ShowRoom"
                port_info = await spider.get_showroom_stream_data(
                    url=url, cookies=self.cookie("showroom")
                )

            elif "acfun.cn" in hostname:
                platform = "Acfun"
                port_info = await spider.get_acfun_stream_data(
                    url=url, cookies=self.cookie("acfun")
                )

            elif "tlclw.com" in hostname:
                platform = "畅聊直播"
                port_info = await spider.get_changliao_stream_url(
                    url=url, cookies=self.cookie("changliao")
                )

            elif "ybw1666.com" in hostname:
                platform = "音播直播"
                port_info = await spider.get_yinbo_stream_url(
                    url=url, cookies=self.cookie("yinbo")
                )

            elif "inke.cn" in hostname:
                platform = "映客直播"
                port_info = await spider.get_yingke_stream_url(
                    url=url, cookies=self.cookie("yingke")
                )

            elif "zhihu.com" in hostname:
                platform = "知乎直播"
                port_info = await spider.get_zhihu_stream_url(
                    url=url, cookies=self.cookie("zhihu")
                )

            elif "chzzk.naver.com" in hostname:
                platform = "CHZZK"
                port_info = await spider.get_chzzk_stream_data(
                    url=url, cookies=self.cookie("chzzk")
                )

            elif "haixiutv.com" in hostname:
                platform = "嗨秀直播"
                port_info = await spider.get_haixiu_stream_url(
                    url=url, cookies=self.cookie("haixiu")
                )

            elif "vvxqiu.com" in hostname:
                platform = "VV星球"
                port_info = await spider.get_vvxqiu_stream_url(
                    url=url, cookies=self.cookie("vvxqiu")
                )

            elif "17.live" in hostname:
                platform = "17Live"
                port_info = await spider.get_17live_stream_url(
                    url=url, cookies=self.cookie("17live")
                )

            elif "lang.live" in hostname:
                platform = "浪Live"
                port_info = await spider.get_langlive_stream_url(
                    url=url, cookies=self.cookie("langlive")
                )

            elif "weimipopo.com" in hostname:
                platform = "漂漂直播"
                port_info = await spider.get_pplive_stream_url(
                    url=url, cookies=self.cookie("pplive")
                )

            elif "6.cn" in hostname:
                platform = "六间房直播"
                port_info = await spider.get_6room_stream_url(
                    url=url, cookies=self.cookie("6room")
                )

            elif "lehaitv.com" in hostname:
                platform = "乐嗨直播"
                # 乐嗨直播与嗨秀直播使用相同的API，由spider内部区分
                port_info = await spider.get_haixiu_stream_url(
                    url=url, cookies=self.cookie("lehaitv")
                )

            elif "catshow168.com" in hostname:
                platform = "花猫直播"
                port_info = await spider.get_pplive_stream_url(
                    url=url, cookies=self.cookie("huamao")
                )

            elif "shopee" in hostname or "shp.ee" in hostname:
                platform = "Shopee"
                port_info = await spider.get_shopee_stream_url(
                    url=url, cookies=self.cookie("shopee")
                )

            elif "youtube.com" in hostname or "youtu.be" in hostname:
                platform = "Youtube"
                port_info = await spider.get_youtube_stream_url(
                    url=url, cookies=self.cookie("youtube")
                )

            elif "tb.cn" in hostname or "taobao.com" in hostname:
                platform = "淘宝直播"
                port_info = await spider.get_taobao_stream_url(
                    url=url, cookies=self.cookie("taobao")
                )

            elif "3.cn" in hostname or "jd.com" in hostname:
                platform = "京东直播"
                port_info = await spider.get_jd_stream_url(
                    url=url, cookies=self.cookie("jd")
                )

            elif "faceit.com" in hostname:
                platform = "faceit"
                port_info = await spider.get_faceit_stream_data(
                    url=url, cookies=self.cookie("faceit")
                )

            elif "miguvideo.com" in hostname:
                platform = "咪咕直播"
                port_info = await spider.get_migu_stream_url(
                    url=url, cookies=self.cookie("migu")
                )

            elif "lailianjie.com" in hostname:
                platform = "连接直播"
                port_info = await spider.get_lianjie_stream_url(
                    url=url, cookies=self.cookie("lianjie")
                )

            elif "imkktv.com" in hostname:
                platform = "来秀直播"
                port_info = await spider.get_laixiu_stream_url(
                    url=url, cookies=self.cookie("laixiu")
                )

            elif "picarto.tv" in hostname:
                platform = "Picarto"
                port_info = await spider.get_picarto_stream_url(
                    url=url, cookies=self.cookie("picarto")
                )

            else:
                return self.status_from_error(source, platform, checked_at, "不支持的直播间地址")

            return self.status_from_port_info(source, platform, checked_at, ensure_dict(port_info))

        except Exception as exc:
            logger.error(f"直播状态检测失败: {source.url} {type(exc).__name__}: {exc}")
            return self.status_from_error(source, platform, checked_at, str(exc))

    def status_from_port_info(
        self,
        source: RoomSource,
        platform: str,
        checked_at: str,
        port_info: dict[str, Any],
    ) -> LiveStatus:
        if not port_info:
            return self.status_from_error(source, platform, checked_at, "直播间信息获取失败")

        anchor_name = source.name or port_info.get("anchor_name", "") or ""
        anchor_name = clean_name(anchor_name, self.settings.clean_emoji) if anchor_name else ""
        return LiveStatus(
            id=source.id,
            url=source.url,
            platform=source.platform or platform,
            is_live=bool(port_info.get("is_live")),
            anchor_name=anchor_name,
            configured_name=source.name,
            title=str(port_info.get("title") or "").strip(),
            cover_url=str(port_info.get("cover_url") or ""),
            avatar_url=str(port_info.get("avatar_url") or ""),
            viewer_count=port_info.get("viewer_count"),
            popularity=port_info.get("popularity"),
            like_count=port_info.get("like_count"),
            area_name=str(port_info.get("area_name") or ""),
            started_at=str(port_info.get("started_at") or ""),
            category=str(port_info.get("category") or ""),
            checked_at=checked_at,
            extra=build_extra(port_info, platform if source.platform and source.platform != platform else ""),
        )

    def status_from_error(self, source: RoomSource, platform: str, checked_at: str, error: str) -> LiveStatus:
        display_error = format_check_error(error)
        return LiveStatus(
            id=source.id,
            url=source.url,
            platform=source.platform or platform,
            is_live=False,
            anchor_name=source.name,
            configured_name=source.name,
            checked_at=checked_at,
            error=display_error,
        )


    def cookie(self, platform: str) -> str:
        return self.settings.cookies.get(platform, "")

    def account(self, key: str) -> str:
        return self.settings.accounts.get(key, "")


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def clean_name(input_text: str, clean_emoji: bool = True) -> str:
    cleaned_name = re.sub(NAME_CLEAN_PATTERN, "_", input_text.strip()).strip("_")
    cleaned_name = cleaned_name.replace("（", "(").replace("）", ")")
    if clean_emoji:
        cleaned_name = utils.remove_emojis(cleaned_name, "_").strip("_")
    return cleaned_name


def ensure_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def copy_extra(target: dict[str, Any], source: Any, key: str) -> None:
    if isinstance(target, dict) and isinstance(source, dict) and source.get(key):
        target[key] = source[key]



def format_check_error(error: str) -> str:
    if not error:
        error = "直播间信息获取失败"
    if "不支持的直播间地址" in error:
        return error
    hint = "检测失败，可能是直播间未开播、地址不可访问或当前网络无法连接该平台。"
    return f"{hint}原始错误：{error}"


def build_extra(port_info: dict[str, Any], detected_platform: str = "") -> dict[str, Any]:
    extra = {key: value for key, value in port_info.items() if key in {"new_cookies", "new_token", "uid"}}
    if detected_platform:
        extra["detected_platform"] = detected_platform
    return extra
