import { Context, Schema } from 'koishi'

export const name = 'live-monitor'

export interface RoomConfig {
  platform?: string
  name?: string
  url: string
  enabled?: boolean
  channels?: string[]
}

export interface Config {
  endpoint: string
  apiToken?: string
  pollInterval: number
  notifyChannels: string[]
  rooms: RoomConfig[]
  notifyOnStart: boolean
  notifyOnEnd: boolean
  notifyOnFirstLive: boolean
  requestTimeout: number
}

export const Config: Schema<Config> = Schema.object({
  endpoint: Schema.string().default('http://127.0.0.1:8000').description('Live Monitor 后端 API 地址'),
  apiToken: Schema.string().role('secret').description('后端 API 访问令牌，对应 config.ini 里的 API访问令牌'),
  pollInterval: Schema.number().min(30).default(300).description('轮询间隔，单位秒'),
  requestTimeout: Schema.number().min(3).default(15).description('请求后端超时时间，单位秒'),
  notifyChannels: Schema.array(String).default([]).description('默认通知频道 ID。为空时只响应命令，不主动推送。'),
  notifyOnStart: Schema.boolean().default(true).description('检测到开播时推送'),
  notifyOnEnd: Schema.boolean().default(false).description('检测到关播时推送'),
  notifyOnFirstLive: Schema.boolean().default(false).description('插件启动后首次检测到已开播也推送'),
  rooms: Schema.array(Schema.object({
    platform: Schema.string().description('平台展示名，例如 抖音、B站、虎牙'),
    name: Schema.string().description('主播展示名，可留空使用后端解析结果'),
    url: Schema.string().required().description('直播间地址'),
    enabled: Schema.boolean().default(true).description('是否启用监控'),
    channels: Schema.array(String).default([]).description('该主播额外通知频道 ID，留空使用默认通知频道'),
  })).role('table').default([]).description('关注主播列表'),
})

interface BackendStatus {
  id: string
  url: string
  platform: string
  is_live: boolean
  anchor_name?: string
  configured_name?: string
  display_name: string
  title?: string
  checked_at?: string
  error?: string
  extra?: Record<string, unknown>
}

function trimSlash(value: string) {
  return value.replace(/\/+$/, '')
}

function roomKey(room: RoomConfig) {
  return `${room.platform || ''}|${room.name || ''}|${room.url}`
}

function formatStatus(status: BackendStatus) {
  const state = status.is_live ? '直播中' : '未开播'
  const platform = status.platform ? `[${status.platform}] ` : ''
  const title = status.title ? `\n标题：${status.title}` : ''
  const error = status.error ? `\n错误：${status.error}` : ''
  return `${platform}${status.display_name || status.url}：${state}${title}${error}\n${status.url}`
}

function formatNotification(status: BackendStatus, started: boolean) {
  const verb = started ? '开播了' : '下播了'
  const platform = status.platform ? `[${status.platform}] ` : ''
  const title = status.title ? `\n标题：${status.title}` : ''
  return `${platform}${status.display_name || status.url} ${verb}${title}\n${status.url}`
}

export function apply(ctx: Context, config: Config) {
  const previous = new Map<string, boolean>()

  async function requestStatus(room: RoomConfig): Promise<BackendStatus> {
    const headers: Record<string, string> = {}
    if (config.apiToken) headers['X-API-Token'] = config.apiToken

    return await ctx.http.post(`${trimSlash(config.endpoint)}/api/check`, {
      platform: room.platform || '',
      name: room.name || '',
      url: room.url,
      trigger_push: false,
    }, {
      headers,
      timeout: config.requestTimeout * 1000,
    })
  }

  async function notify(room: RoomConfig, status: BackendStatus, started: boolean) {
    const channels = [...new Set([...(config.notifyChannels || []), ...((room.channels || []))])]
    if (!channels.length) return
    const message = formatNotification(status, started)
    await ctx.broadcast(channels, message)
  }

  async function checkRoom(room: RoomConfig, manual = false): Promise<BackendStatus | undefined> {
    if (room.enabled === false) return
    try {
      const status = await requestStatus(room)
      const key = roomKey(room)
      const oldState = previous.get(key)
      previous.set(key, status.is_live)

      if (!manual) {
        if (oldState === undefined) {
          if (status.is_live && config.notifyOnFirstLive) await notify(room, status, true)
        } else if (!oldState && status.is_live && config.notifyOnStart) {
          await notify(room, status, true)
        } else if (oldState && !status.is_live && config.notifyOnEnd) {
          await notify(room, status, false)
        }
      }

      return status
    } catch (error) {
      ctx.logger('live-monitor').warn(`检测失败：${room.url} ${error}`)
    }
  }

  async function checkAll(manual = false) {
    const enabledRooms = config.rooms.filter(room => room.enabled !== false && room.url)
    const results: BackendStatus[] = []
    for (const room of enabledRooms) {
      const status = await checkRoom(room, manual)
      if (status) results.push(status)
    }
    return results
  }

  ctx.on('ready', () => {
    void checkAll(false)
  })

  if (config.pollInterval > 0) {
    ctx.setInterval(() => {
      void checkAll(false)
    }, config.pollInterval * 1000)
  }

  ctx.command('live-monitor.status', '查看直播监控状态')
    .action(async () => {
      const statuses = await checkAll(true)
      if (!statuses.length) return '没有启用的直播监控项，或后端暂时不可用。'
      return statuses.map(formatStatus).join('\n\n')
    })

  ctx.command('live-monitor.check', '立即检测直播状态')
    .action(async () => {
      const statuses = await checkAll(true)
      if (!statuses.length) return '没有启用的直播监控项，或后端暂时不可用。'
      return `已检测 ${statuses.length} 个直播间：\n\n${statuses.map(formatStatus).join('\n\n')}`
    })
}
