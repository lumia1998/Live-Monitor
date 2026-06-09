# Live Monitor

Live Monitor 是一个直播间状态监控和提醒服务。它基于原项目的多平台直播状态解析能力，去掉默认直播录制流程，专注于关注主播的开播/关播检测、消息推送和 API 调用。

## 功能

- 监控 `config/URL_config.ini` 中关注的主播直播间。
- 检测开播和关播状态变化，并按配置推送通知。
- 提供 HTTP API，可查询状态、手动检测、增删改关注列表、启动或停止后台监控。
- 默认不返回直播源地址；如确实需要，可在配置中开启。
- 默认不依赖 FFmpeg，不会录制直播视频。

## 支持平台

复用原项目解析能力，支持抖音、TikTok、快手、虎牙、斗鱼、YY、B站、小红书、Bigo、Blued、SOOP、网易 CC、千度热播、PandaTV、猫耳 FM、Look、WinkTV、FlexTV、PopkonTV、TwitCasting、百度、微博、酷狗、Twitch、LiveMe、花椒、流星、ShowRoom、Acfun、映客、音播、知乎、CHZZK、嗨秀、VV星球、17Live、浪Live、畅聊、漂漂、六间房、乐嗨、花猫、Shopee、Youtube、淘宝、京东、Faceit、咪咕、连接、来秀、Picarto 等平台。

所有平台都会先直接检测。若某个平台在当前网络下无法访问，API 会返回检测失败提示；这时可以在 `config/config.ini` 的 `[监控设置]` 中配置代理后再尝试。

## 安装运行

### 1. 本地直接运行

```bash
pip install -r requirements.txt
python main.py
```

启动后默认监听：

```text
http://127.0.0.1:8000
```

### 2. 使用 Docker 部署

#### 本地构建并运行 (Docker CLI)
如果您想直接从本地代码构建镜像并运行：
```bash
# 构建镜像
docker build -t live-monitor:latest .

# 运行容器（挂载配置文件和日志目录以进行持久化，设置时区为上海）
docker run -d \
  --name live-monitor \
  -p 8000:8000 \
  -v ./config:/app/config \
  -v ./logs:/app/logs \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  live-monitor:latest
```

#### 使用 Docker Compose 部署 (推荐)
仓库中已配置好 `docker-compose.yml`。可以直接在项目根目录下执行：
```bash
# 后台构建并启动服务
docker compose up -d --build
```

**Docker Compose 的优势与配置说明**：
- **挂载卷 (Volumes)**：配置文件映射到 `./config`，日志映射到 `./logs`。在宿主机修改配置（如修改监控列表 `config/URL_config.ini` 或核心设置 `config/config.ini`）会直接同步到容器中。
- **时区 (Timezone)**：容器时区已设置为 `Asia/Shanghai`，保证日志和监控定时的时间与国内时间一致。
- **自启动**：`restart: unless-stopped` 保证在系统重启或服务崩溃时容器能够自动拉起。

#### 使用预构建的 GHCR 镜像
项目配置了 GitHub Actions 自动构建工作流。您无需本地构建，即可拉取 GitHub 官方托管的 Docker 镜像：
```bash
docker pull ghcr.io/lumia1998/live-monitor:latest
```
若使用预构建镜像，可在 `docker-compose.yml` 中直接使用 `image: ghcr.io/lumia1998/live-monitor:latest` 并注释/删除 `build: .` 部分。

## 配置关注主播

编辑 `config/URL_config.ini`，一行一个直播间地址：

```text
https://live.douyin.com/745964462470
https://live.bilibili.com/320,平台: B站,主播: 自定义名称
# https://www.huya.com/52333
```

支持格式：

```text
直播间地址
直播间地址,平台: 平台名,主播: 主播名
```

行首加 `#` 表示暂停监控。

## 核心配置

主要配置在 `config/config.ini`：

```ini
[监控设置]
检测间隔(秒) = 300
同一时间访问网络的线程数 = 3
是否使用代理ip(是/否) = 否
代理地址 =
API是否返回直播源地址(是/否) = 否

[API服务]
监听地址 = 0.0.0.0
监听端口 = 8000
API访问令牌 =
是否启动监控后台任务(是/否) = 是
```

如果设置了 `API访问令牌`，API 请求需要带其中一种认证头：

```bash
-H "X-API-Token: your-token"
-H "Authorization: Bearer your-token"
```

## 推送配置

`直播状态推送渠道` 支持多个渠道，用逗号分隔：

```text
微信,钉钉,tg,邮箱,bark,ntfy,pushplus,webhook
```

通用 webhook 会发送 JSON：

```json
{
  "event": "live_started",
  "title": "直播间状态更新通知",
  "content": "...",
  "room": {
    "id": "...",
    "url": "...",
    "platform": "抖音直播",
    "is_live": true,
    "display_name": "..."
  }
}
```

默认首次检测只建立状态基线，不会推送；之后只有离线到在线、在线到离线发生变化时才会推送。


## Koishi 插件调用

仓库内提供了插件草稿：`koishi-plugin-live-monitor/`。

推荐架构：

- 后端用 Docker 部署 Live Monitor，只负责检测直播状态并提供 API。
- Koishi 插件里配置主播列表：平台、主播名、直播地址、是否启用、通知频道。
- 插件定时调用后端 `/api/check`，自己维护状态变化并在 Koishi 里推送提醒。

插件调用后端的请求体示例：

```json
{
  "platform": "抖音",
  "name": "示例主播",
  "url": "https://live.douyin.com/745964462470",
  "trigger_push": false
}
```

这样服务器上的 `config/URL_config.ini` 可以只作为后端本地模式的备用配置；实际使用 Koishi 时，主播配置主要放在 Koishi 插件里。

## API

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

获取缓存状态：

```bash
curl http://127.0.0.1:8000/api/status
```

手动检测所有关注主播：

```bash
curl -X POST http://127.0.0.1:8000/api/check \
  -H "Content-Type: application/json" \
  -d '{}'
```

临时检测一个直播间，不写入关注列表：

```bash
curl -X POST http://127.0.0.1:8000/api/check \
  -H "Content-Type: application/json" \
  -d '{"url":"https://live.douyin.com/745964462470"}'
```

新增关注：

```bash
curl -X POST http://127.0.0.1:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"url":"https://live.bilibili.com/320","platform":"B站","name":"示例主播"}'
```

接口列表：

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

## 旧录制器

旧的录制入口已保留为 `recorder_legacy.py`，用于参考或回退。当前默认入口 `main.py` 不执行录制，不检查 FFmpeg。
