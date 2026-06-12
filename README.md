# Live Monitor

Live Monitor 是一个多平台直播间开播/关播状态检测服务。基于 [DouyinLiveRecorder](https://github.com/ihmily/DouyinLiveRecorder) 的解析能力，去除直播录制流程，专注于状态检测和 HTTP API；通知推送建议交由 Koishi 插件或其他 API 调用方处理。

## 功能特性

- 定时检测 `config/URL_config.ini` 中配置的直播间状态并缓存结果
- 提供 HTTP API，支持查询状态、单个/批量手动检测、动态增删改关注列表、启停后台监控
- 返回丰富的直播元数据：开播状态、直播标题、封面、头像、观看人数、人气、点赞数、分区、开播时间
- 抖音直播间离线时也会尽量保留接口返回的主播名、标题、头像等可用资料
- 不依赖 FFmpeg，不获取直播流地址，不录制视频
- 配置文件热加载，无需重启服务

## 支持平台

抖音、TikTok、快手、虎牙、斗鱼、YY、B站、小红书、Bigo、Blued、SOOP、网易CC、千度热播、PandaTV、猫耳FM、Look、WinkTV、FlexTV、PopkonTV、TwitCasting、百度、微博、酷狗、Twitch、LiveMe、花椒、流星、ShowRoom、Acfun、映客、音播、知乎、CHZZK、嗨秀、VV星球、17Live、浪Live、畅聊、漂漂、六间房、乐嗨、花猫、Shopee、YouTube、淘宝、京东、Faceit、咪咕、连接、来秀、Picarto 等。

> 服务不内置代理配置；无法访问的平台需由运行环境自行解决网络连通性。

## 直播间地址示例

将以下格式的链接写入 `config/URL_config.ini` 即可监控对应直播间。

**抖音**
```
https://live.douyin.com/745964462470
https://v.douyin.com/iQFeBnt/
https://live.douyin.com/yall1102          （可接抖音号）
https://v.douyin.com/CeiU5cbX             （主播主页地址）
```

**TikTok**
```
https://www.tiktok.com/@pearlgaga88/live
```

**快手**
```
https://live.kuaishou.com/u/yall1102
```

**虎牙**
```
https://www.huya.com/52333
```

**斗鱼**
```
https://www.douyu.com/3637778?dyshid=
https://www.douyu.com/topic/wzDBLS6?rid=4921614&dyshid=
```

**YY**
```
https://www.yy.com/22490906/22490906
```

**B站**
```
https://live.bilibili.com/320
```

**小红书**
```
http://xhslink.com/xpJpfM                 （直播间分享地址）
```

**Bigo**
```
https://www.bigo.tv/cn/716418802
```

**Blued**
```
https://app.blued.cn/live?id=Mp6G2R
```

**SOOP**
```
https://play.sooplive.co.kr/sw7love
```

**网易CC**
```
https://cc.163.com/583946984
```

**千度热播**
```
https://qiandurebo.com/web/video.php?roomnumber=33333
```

**PandaTV**
```
https://www.pandalive.co.kr/live/play/bara0109
```

**猫耳FM**
```
https://fm.missevan.com/live/868895007
```

**Look直播**
```
https://look.163.com/live?id=65108820&position=3
```

**WinkTV**
```
https://www.winktv.co.kr/live/play/anjer1004
```

**FlexTV / TTinglive**
```
https://www.flextv.co.kr/channels/593127/live
```

**PopkonTV**
```
https://www.popkontv.com/live/view?castId=wjfal007&partnerCode=P-00117
https://www.popkontv.com/channel/notices?mcid=wjfal007&mcPartnerCode=P-00117
```

**TwitCasting**
```
https://twitcasting.tv/c:uonq
```

**百度直播**
```
https://live.baidu.com/m/media/pclive/pchome/live.html?room_id=9175031377&tab_category
```

**微博直播**
```
https://weibo.com/l/wblive/p/show/1022:2321325026370190442592
```

**酷狗直播**
```
https://fanxing2.kugou.com/50428671?refer=2177&sourceFrom=
```

**Twitch**
```
https://www.twitch.tv/gamerbee
```

**LiveMe**
```
https://www.liveme.com/zh/v/17141543493018047815/index.html
```

**花椒直播**
```
https://www.huajiao.com/l/345096174
```

**流星直播**
```
https://www.7u66.com/100960
```

**ShowRoom**
```
https://www.showroom-live.com/room/profile?room_id=480206  （主播主页地址）
```

**Acfun**
```
https://live.acfun.cn/live/179922
```

**映客直播**
```
https://www.inke.cn/liveroom/index.html?uid=22954469&id=1720860391070904
```

**音播直播**
```
https://live.ybw1666.com/800002949
```

**知乎直播**
```
https://www.zhihu.com/people/ac3a467005c5d20381a82230101308e9  （主播主页地址）
```

**CHZZK**
```
https://chzzk.naver.com/live/458f6ec20b034f49e0fc6d03921646d2
```

**嗨秀直播**
```
https://www.haixiutv.com/6095106
```

**VV星球**
```
https://h5webcdn-pro.vvxqiu.com//activity/videoShare/videoShare.html?h5Server=https://h5p.vvxqiu.com&roomId=LP115924473&platformId=vvstar
```

**17Live**
```
https://17.live/en/live/6302408
```

**浪Live**
```
https://www.lang.live/en-US/room/3349463
```

**畅聊直播**
```
https://live.tlclw.com/106188
```

**漂漂直播**
```
https://m.pp.weimipopo.com/live/preview.html?uid=91648673&anchorUid=91625862&app=plpl
```

**六间房直播**
```
https://v.6.cn/634435
```

**乐嗨直播**
```
https://www.lehaitv.com/8059096
```

**花猫直播**
```
https://h.catshow168.com/live/preview.html?uid=19066357&anchorUid=18895331
```

**Shopee**
```
https://sg.shp.ee/GmpXeuf?uid=1006401066&session=802458
```

**YouTube**
```
https://www.youtube.com/watch?v=cS6zS5hi1w0
```

**淘宝**（需 cookie）
```
https://tbzb.taobao.com/live?liveId=532359023188
https://m.tb.cn/h.TWp0HTd
```

**京东**
```
https://3.cn/28MLBy-E
```

**Faceit**
```
https://www.faceit.com/zh/players/Compl1/stream
```

**咪咕直播**
```
https://www.miguvideo.com/p/live/120000541321
```

**连接直播**
```
https://show.lailianjie.com/10000258
```

**来秀直播**
```
https://www.imkktv.com/h5/share/video.html?uid=1845195&roomId=1710496
```

**Picarto**
```
https://www.picarto.tv/cuteavalanche
```

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
同一时间访问网络的线程数 = 10

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

如果配合 Koishi 插件使用，请在插件的 `apiToken` 配置项中填写同一个令牌。

## API

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查 |
| GET | `/api/status` | 获取后台监控缓存状态 |
| POST | `/api/check` | 手动检测所有关注或单个直播间 |
| POST | `/api/check/batch` | 批量检测多个直播间，适合插件轮询 |
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

# 批量检测多个直播间（不写入关注列表）
curl -X POST http://127.0.0.1:8000/api/check/batch \
  -H "Content-Type: application/json" \
  -d '{"rooms":[{"url":"https://live.douyin.com/745964462470"},{"url":"https://live.bilibili.com/320","name":"示例主播"}]}'

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

推荐配合独立的 [`koishi-plugin-live-monitor`](https://github.com/lumia1998/koishi-plugin-live-monitor) 插件使用，适用于以下架构：

- 后端使用 Docker 部署 Live Monitor，只负责检测状态并提供 API
- Koishi 插件维护主播列表，定时调用后端 `/api/check/batch` 并在 Koishi 内推送提醒

插件调用后端的请求体示例：

```json
{
  "rooms": [
    {
      "platform": "抖音",
      "name": "示例主播",
      "url": "https://live.douyin.com/745964462470"
    }
  ]
}
```

采用此架构时，`config/URL_config.ini` 可留空，主播配置完全由 Koishi 插件管理。

## License

[MIT](LICENSE)
