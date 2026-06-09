# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import datetime as dt
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

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
            proxy_address = self.proxy_for_url(source.url)
            port_info: dict[str, Any] = {}
            url = source.url

            if "douyin.com/" in url:
                platform = "抖音直播"
                if "v.douyin.com" not in url and "/user/" not in url:
                    json_data = await spider.get_douyin_web_stream_data(
                        url=url, proxy_addr=proxy_address, cookies=self.cookie("douyin")
                    )
                else:
                    json_data = await spider.get_douyin_app_stream_data(
                        url=url, proxy_addr=proxy_address, cookies=self.cookie("douyin")
                    )
                port_info = await stream.get_douyin_status(json_data)

            elif "https://www.tiktok.com/" in url:
                platform = "TikTok直播"
                require_proxy(url, proxy_address, platform)
                json_data = await spider.get_tiktok_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("tiktok")
                )
                port_info = await stream.get_tiktok_status(json_data)

            elif "https://live.kuaishou.com/" in url:
                platform = "快手直播"
                json_data = await spider.get_kuaishou_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("kuaishou")
                )
                port_info = await stream.get_kuaishou_status(json_data)

            elif "https://www.huya.com/" in url:
                platform = "虎牙直播"
                json_data = await spider.get_huya_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("huya")
                )
                port_info = await stream.get_huya_status(json_data)

            elif "https://www.douyu.com/" in url:
                platform = "斗鱼直播"
                port_info = await spider.get_douyu_info_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("douyu")
                )

            elif "https://www.yy.com/" in url:
                platform = "YY直播"
                json_data = await spider.get_yy_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("yy")
                )
                port_info = await stream.get_yy_status(json_data)

            elif "https://live.bilibili.com/" in url:
                platform = "B站直播"
                json_data = await spider.get_bilibili_room_info(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("bilibili")
                )
                port_info = await stream.get_bilibili_status(json_data)

            elif "http://xhslink.com/" in url or "https://www.xiaohongshu.com/" in url:
                platform = "小红书直播"
                port_info = await spider.get_xhs_stream_url(
                    url, proxy_addr=proxy_address, cookies=self.cookie("xhs")
                )

            elif "www.bigo.tv/" in url or "slink.bigovideo.tv/" in url:
                platform = "Bigo直播"
                port_info = await spider.get_bigo_stream_url(
                    url, proxy_addr=proxy_address, cookies=self.cookie("bigo")
                )

            elif "https://app.blued.cn/" in url:
                platform = "Blued直播"
                port_info = await spider.get_blued_stream_url(
                    url, proxy_addr=proxy_address, cookies=self.cookie("blued")
                )

            elif "sooplive.co.kr/" in url or "sooplive.com/" in url:
                platform = "SOOP"
                require_proxy(url, proxy_address, platform)
                port_info = await spider.get_sooplive_stream_data(
                    url=url,
                    proxy_addr=proxy_address,
                    cookies=self.cookie("sooplive"),
                    username=self.account("sooplive_username"),
                    password=self.account("sooplive_password"),
                )
                copy_extra(port_info, port_info, "new_cookies")

            elif "cc.163.com/" in url:
                platform = "网易CC直播"
                json_data = await spider.get_netease_stream_data(url=url, cookies=self.cookie("netease"))
                port_info = await stream.get_netease_status(json_data)

            elif "qiandurebo.com/" in url:
                platform = "千度热播"
                port_info = await spider.get_qiandurebo_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("qiandurebo")
                )

            elif "www.pandalive.co.kr/" in url:
                platform = "PandaTV"
                require_proxy(url, proxy_address, platform)
                port_info = await spider.get_pandatv_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("pandatv")
                )

            elif "fm.missevan.com/" in url:
                platform = "猫耳FM直播"
                port_info = await spider.get_maoerfm_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("maoerfm")
                )

            elif "www.winktv.co.kr/" in url:
                platform = "WinkTV"
                require_proxy(url, proxy_address, platform)
                port_info = await spider.get_winktv_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("winktv")
                )

            elif "www.flextv.co.kr/" in url or "www.ttinglive.com/" in url:
                platform = "FlexTV"
                require_proxy(url, proxy_address, platform)
                json_data = await spider.get_flextv_stream_data(
                    url=url,
                    proxy_addr=proxy_address,
                    cookies=self.cookie("flextv"),
                    username=self.account("flextv_username"),
                    password=self.account("flextv_password"),
                )
                port_info = ensure_dict(json_data)
                copy_extra(port_info, port_info, "new_cookies")

            elif "look.163.com/" in url:
                platform = "Look直播"
                port_info = await spider.get_looklive_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("look")
                )

            elif "www.popkontv.com/" in url:
                platform = "PopkonTV"
                require_proxy(url, proxy_address, platform)
                port_info = await spider.get_popkontv_stream_url(
                    url=url,
                    proxy_addr=proxy_address,
                    access_token=self.settings.authorization.get("popkontv_token", ""),
                    username=self.account("popkontv_username"),
                    password=self.account("popkontv_password"),
                    partner_code=self.account("popkontv_partner_code"),
                )

            elif "twitcasting.tv/" in url:
                platform = "TwitCasting"
                port_info = await spider.get_twitcasting_stream_url(
                    url=url,
                    proxy_addr=proxy_address,
                    cookies=self.cookie("twitcasting"),
                    account_type=self.account("twitcasting_account_type"),
                    username=self.account("twitcasting_username"),
                    password=self.account("twitcasting_password"),
                )

            elif "live.baidu.com/" in url:
                platform = "百度直播"
                port_info = await spider.get_baidu_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("baidu")
                )

            elif "weibo.com/" in url:
                platform = "微博直播"
                port_info = await spider.get_weibo_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("weibo")
                )

            elif "kugou.com/" in url:
                platform = "酷狗直播"
                port_info = await spider.get_kugou_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("kugou")
                )

            elif "www.twitch.tv/" in url:
                platform = "TwitchTV"
                port_info = await spider.get_twitchtv_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("twitch")
                )

            elif "www.liveme.com/" in url:
                platform = "LiveMe"
                require_proxy(url, proxy_address, platform)
                port_info = await spider.get_liveme_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("liveme")
                )

            elif "www.huajiao.com/" in url:
                platform = "花椒直播"
                port_info = await spider.get_huajiao_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("huajiao")
                )

            elif "7u66.com/" in url:
                platform = "流星直播"
                port_info = await spider.get_liuxing_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("liuxing")
                )

            elif "showroom-live.com/" in url:
                platform = "ShowRoom"
                port_info = await spider.get_showroom_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("showroom")
                )

            elif "live.acfun.cn/" in url or "m.acfun.cn/" in url:
                platform = "Acfun"
                port_info = await spider.get_acfun_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("acfun")
                )

            elif "live.tlclw.com/" in url:
                platform = "畅聊直播"
                port_info = await spider.get_changliao_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("changliao")
                )

            elif "ybw1666.com/" in url:
                platform = "音播直播"
                port_info = await spider.get_yinbo_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("yinbo")
                )

            elif "www.inke.cn/" in url:
                platform = "映客直播"
                port_info = await spider.get_yingke_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("yingke")
                )

            elif "www.zhihu.com/" in url:
                platform = "知乎直播"
                port_info = await spider.get_zhihu_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("zhihu")
                )

            elif "chzzk.naver.com/" in url:
                platform = "CHZZK"
                require_proxy(url, proxy_address, platform)
                port_info = await spider.get_chzzk_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("chzzk")
                )

            elif "www.haixiutv.com/" in url:
                platform = "嗨秀直播"
                port_info = await spider.get_haixiu_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("haixiu")
                )

            elif "vvxqiu.com/" in url:
                platform = "VV星球"
                port_info = await spider.get_vvxqiu_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("vvxqiu")
                )

            elif "17.live/" in url:
                platform = "17Live"
                port_info = await spider.get_17live_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("17live")
                )

            elif "www.lang.live/" in url:
                platform = "浪Live"
                port_info = await spider.get_langlive_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("langlive")
                )

            elif "m.pp.weimipopo.com/" in url:
                platform = "漂漂直播"
                port_info = await spider.get_pplive_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("pplive")
                )

            elif ".6.cn/" in url:
                platform = "六间房直播"
                port_info = await spider.get_6room_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("6room")
                )

            elif "lehaitv.com/" in url:
                platform = "乐嗨直播"
                port_info = await spider.get_haixiu_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("lehaitv")
                )

            elif "h.catshow168.com/" in url:
                platform = "花猫直播"
                port_info = await spider.get_pplive_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("huamao")
                )

            elif "live.shopee" in url or "shp.ee/" in url:
                platform = "Shopee"
                port_info = await spider.get_shopee_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("shopee")
                )

            elif "www.youtube.com/" in url or "youtu.be/" in url:
                platform = "Youtube"
                port_info = await spider.get_youtube_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("youtube")
                )

            elif "tb.cn" in url or "taobao.com/" in url:
                platform = "淘宝直播"
                port_info = await spider.get_taobao_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("taobao")
                )

            elif "3.cn" in url or "m.jd.com" in url:
                platform = "京东直播"
                port_info = await spider.get_jd_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("jd")
                )

            elif "faceit.com/" in url:
                platform = "faceit"
                require_proxy(url, proxy_address, platform)
                port_info = await spider.get_faceit_stream_data(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("faceit")
                )

            elif "www.miguvideo.com" in url or "m.miguvideo.com" in url:
                platform = "咪咕直播"
                port_info = await spider.get_migu_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("migu")
                )

            elif "show.lailianjie.com" in url:
                platform = "连接直播"
                port_info = await spider.get_lianjie_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("lianjie")
                )

            elif "www.imkktv.com" in url:
                platform = "来秀直播"
                port_info = await spider.get_laixiu_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("laixiu")
                )

            elif "www.picarto.tv" in url:
                platform = "Picarto"
                port_info = await spider.get_picarto_stream_url(
                    url=url, proxy_addr=proxy_address, cookies=self.cookie("picarto")
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

    def proxy_for_url(self, url: str) -> str | None:
        if not self.settings.use_proxy or not self.settings.proxy_addr:
            return None
        tokens = self.settings.proxy_platforms + self.settings.extra_proxy_platforms
        if not tokens:
            return self.settings.proxy_addr
        for token in tokens:
            if token and token.strip().lower() in url.lower():
                return self.settings.proxy_addr
        return None

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


def require_proxy(url: str, proxy_address: str | None, platform: str) -> None:
    return None


def format_check_error(error: str) -> str:
    if not error:
        error = "直播间信息获取失败"
    if "不支持的直播间地址" in error:
        return error
    hint = "检测失败，可能是直播间未开播、地址不可访问或当前网络无法连接该平台；如果一直失败，请开启代理后再尝试。"
    return f"{hint}原始错误：{error}"


def build_extra(port_info: dict[str, Any], detected_platform: str = "") -> dict[str, Any]:
    extra = {key: value for key, value in port_info.items() if key in {"new_cookies", "new_token", "uid"}}
    if detected_platform:
        extra["detected_platform"] = detected_platform
    return extra
