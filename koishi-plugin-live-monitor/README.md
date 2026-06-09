# koishi-plugin-live-monitor

这个 Koishi 插件用于调用 Live Monitor 后端 API，定时检测直播间开播/关播状态，并向指定频道发送提醒。

## 架构

- Live Monitor 后端：Docker 部署，提供 `/api/check`。
- Koishi 插件：在 Koishi 控制台配置平台、主播名、直播地址、通知频道，然后轮询后端。
- 主播列表以 Koishi 插件配置为准，后端不需要手动维护 `URL_config.ini`。

## 后端配置

后端默认地址：

```text
http://127.0.0.1:8000
```

如果设置了后端 API token：

```ini
[API服务]
API访问令牌 = your-token
```

插件配置里也填同一个 token。

## 插件配置

主播列表字段：

| 字段 | 说明 |
| --- | --- |
| platform | 平台展示名，例如 抖音、B站、虎牙 |
| name | 主播展示名，可留空 |
| url | 直播间地址 |
| enabled | 是否启用 |
| channels | 该主播额外通知频道，留空使用默认通知频道 |

插件会调用：

```http
POST /api/check
```

请求体示例：

```json
{
  "platform": "抖音",
  "name": "示例主播",
  "url": "https://live.douyin.com/745964462470",
  "trigger_push": false
}
```

## 命令

```text
live-monitor.status
live-monitor.check
```

`status` 查看当前配置里的直播状态；`check` 立即检测一次。

## 注意

首次轮询只建立状态基线，默认不会对“已经开播”的直播间推送。需要启动时也提醒的话，开启 `notifyOnFirstLive`。
