import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchScreenData } from '@/api'
import type { ScreenData } from '@/types'

/**
 * 大屏口径（授权版本）跨窗口同步。
 * 版本号存 localStorage：任一窗口发现口径更新（409 或主动刷新）后广播，
 * 其它窗口收到 storage 事件立即切到同一版本重取数据 —— 同一账号多个
 * 窗口永远展示同一个已发布版本 + 服务端按版本确定性生成的数据。
 */
const VERSION_KEY = 'lad_screen_version'

export function readSharedVersion(): number | undefined {
  const v = localStorage.getItem(VERSION_KEY)
  return v == null ? undefined : Number(v)
}
export function writeSharedVersion(version: number) {
  if (readSharedVersion() !== version) localStorage.setItem(VERSION_KEY, String(version))
}

export const useScreenStore = defineStore('screen', () => {
  const active = ref(false)
  const data = ref<ScreenData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastUpdated = ref<string>('')
  const logType = ref('nginx')
  let timer: number | null = null

  async function load(version?: number) {
    loading.value = true
    error.value = null
    try {
      const d = await fetchScreenData(logType.value, version)
      data.value = d
      writeSharedVersion(d.scope.version)
      lastUpdated.value = new Date().toLocaleTimeString()
    } catch (e: unknown) {
      const reason = (e as { reason?: string }).reason || '大屏数据加载失败'
      error.value = reason
      // 409：授权版本已更新 -> 用最新版本重取一次，不向用户展示旧口径
      if (reason.includes('授权口径已更新')) {
        const m = reason.match(/当前为 v(\d+)/)
        if (m) return load(Number(m[1]))
      }
      throw e
    } finally {
      loading.value = false
    }
  }

  async function open(type: string) {
    active.value = true
    logType.value = type
    await load(readSharedVersion())
    if (timer == null) {
      timer = window.setInterval(() => { void load(readSharedVersion()) }, 30_000)
    }
  }

  async function changeType(type: string) {
    logType.value = type
    await load(readSharedVersion())
  }

  function close() {
    active.value = false
    data.value = null
    error.value = null
    if (timer != null) { clearInterval(timer); timer = null }
  }

  /** storage 事件：其它窗口切了授权版本，本窗口立即跟随，保证口径一致 */
  function onStorage(ev: StorageEvent) {
    if (!active.value || ev.key !== VERSION_KEY || ev.newValue == null) return
    const next = Number(ev.newValue)
    if (data.value && next !== data.value.scope.version) void load(next)
  }
  window.addEventListener('storage', onStorage)

  return { active, data, loading, error, lastUpdated, logType, open, close, changeType, load }
})
