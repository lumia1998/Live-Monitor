# -*- coding: utf-8 -*-
from __future__ import annotations

import configparser
import hashlib
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_FILE = PROJECT_ROOT / "config" / "config.ini"
DEFAULT_URL_CONFIG_FILE = PROJECT_ROOT / "config" / "URL_config.ini"
TEXT_ENCODING = "utf-8-sig"

QUALITY_LABELS = ("原画", "蓝光", "超清", "高清", "标清", "流畅")
DEFAULT_PROXY_PLATFORMS = (
    "tiktok, soop, sooplive, pandalive, winktv, flextv, ttinglive, popkontv, "
    "twitch, liveme, showroom, chzzk, shopee, shp, youtu, youtube, faceit"
)

COOKIE_OPTIONS = {
    "douyin": "抖音cookie",
    "kuaishou": "快手cookie",
    "tiktok": "tiktok_cookie",
    "huya": "虎牙cookie",
    "douyu": "斗鱼cookie",
    "yy": "yy_cookie",
    "bilibili": "B站cookie",
    "xhs": "小红书cookie",
    "bigo": "bigo_cookie",
    "blued": "blued_cookie",
    "sooplive": "sooplive_cookie",
    "netease": "netease_cookie",
    "qiandurebo": "千度热播_cookie",
    "pandatv": "pandatv_cookie",
    "maoerfm": "猫耳fm_cookie",
    "winktv": "winktv_cookie",
    "flextv": "flextv_cookie",
    "look": "look_cookie",
    "twitcasting": "twitcasting_cookie",
    "baidu": "baidu_cookie",
    "weibo": "weibo_cookie",
    "kugou": "kugou_cookie",
    "twitch": "twitch_cookie",
    "liveme": "liveme_cookie",
    "huajiao": "huajiao_cookie",
    "liuxing": "liuxing_cookie",
    "showroom": "showroom_cookie",
    "acfun": "acfun_cookie",
    "changliao": "changliao_cookie",
    "yinbo": "yinbo_cookie",
    "yingke": "yingke_cookie",
    "zhihu": "zhihu_cookie",
    "chzzk": "chzzk_cookie",
    "haixiu": "haixiu_cookie",
    "vvxqiu": "vvxqiu_cookie",
    "17live": "17live_cookie",
    "langlive": "langlive_cookie",
    "pplive": "pplive_cookie",
    "6room": "6room_cookie",
    "lehaitv": "lehaitv_cookie",
    "huamao": "huamao_cookie",
    "shopee": "shopee_cookie",
    "youtube": "youtube_cookie",
    "taobao": "taobao_cookie",
    "jd": "jd_cookie",
    "faceit": "faceit_cookie",
    "migu": "migu_cookie",
    "lianjie": "lianjie_cookie",
    "laixiu": "laixiu_cookie",
    "picarto": "picarto_cookie",
}

ACCOUNT_OPTIONS = {
    "sooplive_username": ("账号密码", "sooplive账号", ""),
    "sooplive_password": ("账号密码", "sooplive密码", ""),
    "flextv_username": ("账号密码", "flextv账号", ""),
    "flextv_password": ("账号密码", "flextv密码", ""),
    "popkontv_username": ("账号密码", "popkontv账号", ""),
    "popkontv_password": ("账号密码", "popkontv密码", ""),
    "popkontv_partner_code": ("账号密码", "partner_code", "P-00001"),
    "twitcasting_account_type": ("账号密码", "twitcasting账号类型", "normal"),
    "twitcasting_username": ("账号密码", "twitcasting账号", ""),
    "twitcasting_password": ("账号密码", "twitcasting密码", ""),
}


@dataclass(slots=True)
class RoomSource:
    url: str
    platform: str = ""
    quality: str = "原画"
    name: str = ""
    enabled: bool = True
    raw_line: str = ""

    @property
    def id(self) -> str:
        return hashlib.sha1(self.url.encode("utf-8")).hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "platform": self.platform,
            "name": self.name,
            "enabled": self.enabled,
        }




@dataclass(slots=True)
class ApiSettings:
    host: str = "0.0.0.0"
    port: int = 8000
    token: str = ""
    start_background_monitor: bool = True


@dataclass(slots=True)
class RuntimeSettings:
    config_file: Path
    url_config_file: Path
    default_quality: str = "原画"
    check_interval: int = 60
    max_concurrency: int = 3
    use_proxy: bool = False
    proxy_addr: str = ""
    proxy_platforms: list[str] = field(default_factory=list)
    extra_proxy_platforms: list[str] = field(default_factory=list)
    clean_emoji: bool = True
    include_stream_url: bool = False
    cookies: dict[str, str] = field(default_factory=dict)
    accounts: dict[str, str] = field(default_factory=dict)
    authorization: dict[str, str] = field(default_factory=dict)
    api: ApiSettings = field(default_factory=ApiSettings)


def split_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,，|]", value) if item.strip()]


def normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if url and "://" not in url:
        url = "https://" + url
    return url


def contains_url(value: str) -> bool:
    pattern = r"(https?://)?(www\.)?[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(:\d+)?(/.*)?"
    return re.search(pattern, value.strip()) is not None


def normalize_quality(value: str, default: str = "原画") -> str:
    value = (value or default).strip()
    return value if value in QUALITY_LABELS else default


def clean_configured_name(value: str) -> str:
    return clean_labeled_value(value, "主播")


def clean_configured_platform(value: str) -> str:
    return clean_labeled_value(value, "平台")


def clean_labeled_value(value: str, label: str) -> str:
    value = (value or "").strip()
    prefix = f"{label}:"
    full_width_prefix = f"{label}："
    if value.startswith(prefix):
        value = value.split(prefix, maxsplit=1)[1]
    elif value.startswith(full_width_prefix):
        value = value.split(full_width_prefix, maxsplit=1)[1]
    return value.strip()


def parse_room_line(line: str, default_quality: str = "原画") -> RoomSource | None:
    raw_line = line.rstrip("\n")
    stripped = raw_line.strip()
    if not stripped:
        return None

    enabled = not stripped.startswith("#")
    if not enabled:
        stripped = stripped.lstrip("#").strip()
    if not stripped:
        return None

    parts = [part.strip() for part in re.split(r"[,，]", stripped, maxsplit=3) if part.strip()]
    quality = default_quality
    platform = ""
    name = ""
    metadata: list[str] = []

    if len(parts) == 1:
        url = parts[0]
    elif parts[0] in QUALITY_LABELS and len(parts) >= 2:
        # 兼容旧格式：清晰度,直播间地址,主播: 名称,平台: 平台。
        quality = parts[0]
        url = parts[1]
        metadata = parts[2:]
    else:
        url = parts[0]
        metadata = parts[1:]

    for item in metadata:
        if item.startswith(("主播:", "主播：")):
            name = clean_configured_name(item)
        elif item.startswith(("平台:", "平台：")):
            platform = clean_configured_platform(item)
        elif not name:
            name = clean_configured_name(item)

    url = normalize_url(url)
    if not contains_url(url):
        return None

    return RoomSource(
        url=url,
        platform=platform,
        quality=normalize_quality(quality, default_quality),
        name=clean_configured_name(name),
        enabled=enabled,
        raw_line=raw_line,
    )


def format_room_line(source: RoomSource) -> str:
    line = source.url
    if source.platform:
        line += f",平台: {source.platform}"
    if source.name:
        line += f",主播: {source.name}"
    if not source.enabled:
        line = "#" + line
    return line


class ConfigStore:
    def __init__(
        self,
        config_file: str | Path = DEFAULT_CONFIG_FILE,
        url_config_file: str | Path = DEFAULT_URL_CONFIG_FILE,
    ) -> None:
        self.config_file = Path(config_file)
        self.url_config_file = Path(url_config_file)
        self._lock = threading.RLock()
        self.ensure_files()

    def ensure_files(self) -> None:
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.url_config_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self.config_file.write_text("", encoding=TEXT_ENCODING)
        if not self.url_config_file.exists():
            self.url_config_file.write_text("", encoding=TEXT_ENCODING)

    def _parser(self) -> configparser.RawConfigParser:
        parser = configparser.RawConfigParser()
        parser.read(self.config_file, encoding=TEXT_ENCODING)
        return parser

    def _get(self, parser: configparser.RawConfigParser, section: str, option: str, default: str) -> str:
        if not parser.has_section(section):
            parser.add_section(section)
            parser.set(section, option, str(default))
            return str(default)
        if not parser.has_option(section, option):
            parser.set(section, option, str(default))
            return str(default)
        return parser.get(section, option).strip()

    def _write_parser(self, parser: configparser.RawConfigParser) -> None:
        with self.config_file.open("w", encoding=TEXT_ENCODING) as fp:
            parser.write(fp)

    def get_value(self, section: str, option: str, default: str = "") -> str:
        with self._lock:
            parser = self._parser()
            value = self._get(parser, section, option, default)
            self._write_parser(parser)
            return value

    def set_value(self, section: str, option: str, value: str) -> None:
        with self._lock:
            parser = self._parser()
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, option, value)
            self._write_parser(parser)

    def load_runtime_settings(self) -> RuntimeSettings:
        with self._lock:
            parser = self._parser()
            original_sections = {s: dict(parser.items(s)) for s in parser.sections()}

            def get(section: str, option: str, default: str = "") -> str:
                return self._get(parser, section, option, default)

            def get_bool(section: str, option: str, default: str = "否") -> bool:
                return get(section, option, default).lower() in {"是", "yes", "true", "1", "on"}

            def get_int(section: str, option: str, default: int) -> int:
                try:
                    return int(get(section, option, str(default)))
                except ValueError:
                    return default

            api = ApiSettings(
                host=get("API服务", "监听地址", "0.0.0.0"),
                port=get_int("API服务", "监听端口", 8000),
                token=get("API服务", "API访问令牌", ""),
                start_background_monitor=get_bool("API服务", "是否启动监控后台任务(是/否)", "是"),
            )

            settings = RuntimeSettings(
                config_file=self.config_file,
                url_config_file=self.url_config_file,
                default_quality="原画",
                check_interval=max(get_int("监控设置", "检测间隔(秒)", 60), 10),
                max_concurrency=max(get_int("监控设置", "同一时间访问网络的线程数", 3), 1),
                use_proxy=get_bool("监控设置", "是否使用代理ip(是/否)", "否"),
                proxy_addr=get("监控设置", "代理地址", ""),
                proxy_platforms=split_csv(get("监控设置", "使用代理的平台(逗号分隔)", DEFAULT_PROXY_PLATFORMS)),
                extra_proxy_platforms=split_csv(get("监控设置", "额外使用代理的平台(逗号分隔)", "")),
                clean_emoji=get_bool("监控设置", "是否去除名称中的表情符号", "是"),
                include_stream_url=get_bool("监控设置", "API是否返回直播源地址(是/否)", "否"),
                cookies={key: get("Cookie", option, "") for key, option in COOKIE_OPTIONS.items()},
                accounts={key: get(section, option, default) for key, (section, option, default) in ACCOUNT_OPTIONS.items()},
                authorization={"popkontv_token": get("Authorization", "popkontv_token", "")},
                api=api,
            )

            new_sections = {s: dict(parser.items(s)) for s in parser.sections()}
            if new_sections != original_sections:
                self._write_parser(parser)

            return settings

    def load_room_sources(self, include_disabled: bool = True) -> list[RoomSource]:
        settings = self.load_runtime_settings()
        with self._lock:
            sources: list[RoomSource] = []
            seen: set[str] = set()
            for line in self.url_config_file.read_text(encoding=TEXT_ENCODING).splitlines():
                source = parse_room_line(line, settings.default_quality)
                if not source or source.url in seen:
                    continue
                seen.add(source.url)
                if include_disabled or source.enabled:
                    sources.append(source)
            return sources

    def save_room_sources(self, sources: list[RoomSource]) -> None:
        with self._lock:
            lines = [format_room_line(source) for source in sources]
            content = "\n".join(lines)
            if content:
                content += "\n"
            self.url_config_file.write_text(content, encoding=TEXT_ENCODING)

    def add_room(self, url: str, platform: str = "", name: str = "", enabled: bool = True) -> RoomSource:
        with self._lock:
            sources = self.load_room_sources(include_disabled=True)
            normalized_url = normalize_url(url)
            new_source = RoomSource(
                url=normalized_url,
                platform=clean_configured_platform(platform),
                quality="原画",
                name=clean_configured_name(name),
                enabled=enabled,
            )
            for index, source in enumerate(sources):
                if source.url == normalized_url:
                    sources[index] = new_source
                    self.save_room_sources(sources)
                    return new_source
            sources.append(new_source)
            self.save_room_sources(sources)
            return new_source

    def find_room(self, room_id: str) -> RoomSource | None:
        for source in self.load_room_sources(include_disabled=True):
            if source.id == room_id:
                return source
        return None

    def update_room(
        self,
        room_id: str,
        *,
        platform: str | None = None,
        name: str | None = None,
        enabled: bool | None = None,
    ) -> RoomSource | None:
        with self._lock:
            sources = self.load_room_sources(include_disabled=True)
            for index, source in enumerate(sources):
                if source.id != room_id:
                    continue
                if platform is not None:
                    source.platform = clean_configured_platform(platform)
                if name is not None:
                    source.name = clean_configured_name(name)
                if enabled is not None:
                    source.enabled = enabled
                sources[index] = source
                self.save_room_sources(sources)
                return source
            return None

    def delete_room(self, room_id: str) -> RoomSource | None:
        with self._lock:
            sources = self.load_room_sources(include_disabled=True)
            kept: list[RoomSource] = []
            deleted: RoomSource | None = None
            for source in sources:
                if source.id == room_id:
                    deleted = source
                else:
                    kept.append(source)
            if deleted:
                self.save_room_sources(kept)
            return deleted
