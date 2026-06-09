# Live Monitor

Live Monitor 是一个多平台直播间开播/关播监控和提醒服务。基于 [DouyinLiveRecorder](https://github.com/ihmily/DouyinLiveRecorder) 的解析能力，去除直播录制流程，专注于状态检测、消息推送和 HTTP API。

## 功能特性

- 定时检测 `config/URL_config.ini` 中配置的直播间状态
- 开播/关播变化时自动推送通知（支持多渠道）
- 提供 HTTP API，支持查询状态、手动检测、动态增删改关注列表、启停后台监控
- 返回丰富的直播元数据：开播状态、直播标题、封面、头像、观看人数、人气、点赞数、分区、开播时间
- 抖音直播间离线时也会尽量保留接口返回的主播名、标题、头像等可用资料
- 不依赖 FFmpeg，不获取直播流地址，不录制视频
- 支持代理配置（针对国内无法访问的平台）
- 配置文件热加载，无需重启服务

## 支持平台

抖音、TikTok、快手、虎牙、斗鱼、YY、B站、小红书、Bigo、Blued、SOOP、网易CC、千度热播、PandaTV、猫耳FM、Look、WinkTV、FlexTV、PopkonTV、TwitCasting、百度、微博、酷狗、Twitch、LiveMe、花椒、流星、ShowRoom、Acfun、映客、音播、知乎、CHZZK、嗨秀、VV星球、17Live、浪Live、畅聊、漂漂、六间房、乐嗨、花猫、Shopee、YouTube、淘宝、京东、Faceit、咪咕、连接、来秀、Picarto 等。

> 所有平台均直接检测，无法访问的平台可在配置中启用代理。

## 部署

### Docker Compose（推荐）

将以下 `docker-compose.yml` 复制到服务器任意目录，执行启动命令即可，无需下载源码。

```yaml
services:
  live-monitor:
    image: ghcr.io/lumia1998/live-monitor:latest
    container_name: live-monitor
    environment:
      - TZ=Asia/Shanghai
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    restart: unless-stopped
```

```bash
docker compose up -d
```

首次启动时，容器会在 `./config` 目录下自动生成 `config.ini` 和 `URL_config.ini` 两个配置文件。

### Docker CLI

```bash
docker run -d \
  --name live-monitor \
  -p 8000:8000 \
  -v ./config:/app/config \
  -v ./logs:/app/logs \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  ghcr.io/lumia1998/live-monitor:latest
```

### 本地运行

需要 Python 3.10+，并已安装 Node.js（部分平台的 JS 解析依赖）。

```bash
pip install -r requirements.txt
python main.py
```

启动后默认监听 `http://127.0.0.1:8000`。

## 配置

### 添加监控主播

编辑 `config/URL_config.ini`，一行一个直播间：

```ini
https://live.douyin.com/745964462470
https://live.bilibili.com/320,平台: B站,主播: 自定义名称
# https://www.huya.com/52333
```

- 支持格式：`直播间地址` 或 `直播间地址,平台: 平台名,主播: 主播名`
- 行首加 `#` 表示暂停监控该直播间
- 修改后无需重启，下次检测周期自动生效

### 核心配置

编辑 `config/config.ini`：

```ini
[监控设置]
检测间隔(秒) = 60
同一时间访问网络的线程数 = 3
是否使用代理ip(是/否) = 否
代理地址 =

[API服务]
监听地址 = 0.0.0.0
监听端口 = 8000
API访问令牌 =
是否启动监控后台任务(是/否) = 是
```

### API 认证

若设置了 `API访问令牌`，所有需要认证的接口请求须携带以下任一 Header：

```
X-API-Token: your-token
Authorization: Bearer your-token
```

## API

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查 |
| GET | `/api/status` | 获取后台监控缓存状态 |
| POST | `/api/check` | 手动检测所有关注或单个直播间 |
| GET | `/api/rooms` | 获取关注列表 |
| POST | `/api/rooms` | 新增或覆盖关注 |
| PATCH | `/api/rooms/{room_id}` | 修改关注配置 |
| DELETE | `/api/rooms/{room_id}` | 删除关注 |
| POST | `/api/monitor/start` | 启动后台监控 |
| POST | `/api/monitor/stop` | 停止后台监控 |

### 使用示例

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 获取后台监控状态
curl http://127.0.0.1:8000/api/status

# 手动检测所有关注主播
curl -X POST http://127.0.0.1:8000/api/check \
  -H "Content-Type: application/json" \
  -d '{}'

# 临时检测一个直播间（不写入关注列表）
curl -X POST http://127.0.0.1:8000/api/check \
  -H "Content-Type: application/json" \
  -d '{"url":"https://live.douyin.com/745964462470"}'

# 新增关注
curl -X POST http://127.0.0.1:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"url":"https://live.bilibili.com/320","platform":"B站","name":"示例主播"}'
```

### 直播时长字段

后端会在首次检测到直播间开播时记录 `detected_started_at`，并在之后的检测结果中返回 `live_duration_seconds` 与格式化后的 `live_duration`。这个时间按后端进程检测到开播的时间计算，不等同于平台真实开播时间；后端重启后会重新统计。

直播状态响应中的相关字段示例：

```json
{
  "is_live": true,
  "started_at": "",
  "detected_started_at": "2026-06-09T22:31:00+08:00",
  "live_duration_seconds": 125,
  "live_duration": "2分钟"
}
```

## Koishi 插件

仓库内提供了 Koishi 插件草稿（`koishi-plugin-live-monitor/`），适用于以下架构：

- 后端使用 Docker 部署 Live Monitor，只负责检测状态并提供 API
- Koishi 插件维护主播列表，定时调用后端 `/api/check` 并在 Koishi 内推送提醒

插件调用后端的请求体示例：

```json
{
  "platform": "抖音",
  "name": "示例主播",
  "url": "https://live.douyin.com/745964462470",
  "trigger_push": false
}
```

采用此架构时，`config/URL_config.ini` 可留空，主播配置完全由 Koishi 插件管理。

## License

[MIT](LICENSE)
