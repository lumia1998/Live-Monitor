# -*- coding: utf-8 -*-
from __future__ import annotations

import uvicorn

from src.monitor_config import ConfigStore


VERSION = "v1.0.0-monitor"


def main() -> None:
    store = ConfigStore()
    settings = store.load_runtime_settings()
    print("-----------------------------------------------------")
    print("|                    Live Monitor                   |")
    print("-----------------------------------------------------")
    print(f"版本号: {VERSION}")
    print("模式: 直播状态检测 + API，不执行直播录制和通知推送")
    print(f"API: http://{settings.api.host}:{settings.api.port}")
    print(".....................................................")
    uvicorn.run("api_server:app", host=settings.api.host, port=settings.api.port, reload=False)


if __name__ == "__main__":
    main()
