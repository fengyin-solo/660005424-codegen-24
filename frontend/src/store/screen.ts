import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import type { Grant, ScreenAccount, ScreenCatalog, ScreenData, ScreenApiError, EffectiveScope } from '@/types'

const CHANNEL_NAME = 'log-platform-screen-permission'
const STORAGE_KEY = 'screen-permission-state-v1'

interface CrossTabMessage {
  type: 'account-changed' | 'enable-changed'
  account: string
  enabled?: boolean
  version?: number
  at: number
}

function channel(): BroadcastChannel | null {
  return typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel(CHANNEL_NAME) : null
}

function postCrossTab(msg: Omit<CrossTabMessage, 'at'>) {
  const payload: CrossTabMessage = { ...msg, at: Date.now() }
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(payload)) } catch { /* ignore */ }
  const bc = channel()
  if (bc) { bc.postMessage(payload); bc.close() }
}

export const useScreenStore = defineStore('screen', () => {
    const accounts = ref<ScreenAccount[]>([])
    const catalog = ref<ScreenCatalog>({ sources: [], levels: [] })
    const currentAccount = ref<string>('')
    const data = ref<ScreenData | null>(null)
    const loading = ref(false)
    const error = ref<ScreenApiError | null>(null)
    const lastFetchedVersion = ref<number>(0)

    function currentMeta(): ScreenAccount | undefined {
      return accounts.value.find(a => a.account === currentAccount.value)
    }

    async function loadCatalog() {
      if (!catalog.value.sources.length) {
        const { data: d } = await axios.get<ScreenCatalog>('/api/screen/catalog')
        catalog.value = d
      }
      return catalog.value
    }

    async function loadAccounts() {
      const { data } = await axios.get('/api/screen/accounts')
      accounts.value = data.accounts
    }

    /** 选择大屏账号。跨窗口广播：同一账号在所有窗口看到的取值口径必须一致。 */
    async function selectAccount(account: string) {
      currentAccount.value = account
      data.value = null
      error.value = null
      postCrossTab({ type: 'account-changed', account })
      await loadData()
    }

    async function loadData(opts?:{ silent?: boolean }): Promise<boolean> {
      if (!currentAccount.value) return false
      if (!opts?.silent) loading.value = true
      error.value = null
      try {
        const { data: d } = await axios.post<ScreenData>('/api/screen/data', { account: currentAccount.value })
        data.value = d
        lastFetchedVersion.value = d.version
        const meta = currentMeta()
        if (meta) { meta.enabled = true; meta.version = d.version; meta.effectiveScope = d.scope }
        return true
      } catch (e: any) {
        data.value = null
        error.value = (e?.response?.data?.detail ?? {
          code: 'network_error',
          message: e?.message || '大屏数据请求失败',
        }) as ScreenApiError
        return false
      } finally {
        loading.value = false
      }
    }

    /**
     * 保存授权清单并启用/停用。
     * 启用失败时后端逐字返回不合格项；这里原样抛出供界面展示说明。
     */
    async function saveConfig(account: string, grants: Grant[], enabled: boolean) {
      const { data } = await axios.post(`/api/screen/config/${account}`, { grants, enabled })
      await loadAccounts()
      if (enabled) {
        postCrossTab({ type: 'enable-changed', account, enabled: true, version: data.version })
        if (account === currentAccount.value) await loadData()
      } else {
        postCrossTab({ type: 'enable-changed', account, enabled: false })
        if (account === currentAccount.value) data.value = null
      }
      return data as { ok: boolean; enabled: boolean; version: number; message: string; effectiveScope: EffectiveScope }
    }

    async function disable(account: string) {
      await axios.post(`/api/screen/disable/${account}`)
      await loadAccounts()
      postCrossTab({ type: 'enable-changed', account, enabled: false })
      if (account === currentAccount.value) { data.value = null; error.value = null }
    }

    /** 显式请求可能越权的对象；成功返回数据，失败把含原因的错误抛出。 */
    async function requestScoped(account: string, body: { sources?: string[]; levels?: string[] }) {
      return axios.post('/api/screen/data', { account, ...body })
    }

    function effectiveScopeOf(grants: Grant[]): EffectiveScope {
      const allow = (dim: string) => new Set(grants.filter(g => g.dimension === dim && g.action === 'allow').map(g => g.value))
      const deny = (dim: string) => new Set(grants.filter(g => g.dimension === dim && g.action === 'deny').map(g => g.value))
      const pick = (dim: string) => [...allow(dim)].filter(v => !deny(dim).has(v)).sort()
      return { sources: pick('source'), levels: pick('level') }
    }

    /** 同步外部（其他窗口）广播过来的口径变化。 */
    async function handleCrossTab(msg: CrossTabMessage) {
      await loadAccounts()
      if (msg.type === 'account-changed') {
        if (currentAccount.value !== msg.account) {
          currentAccount.value = msg.account
          await loadData()
        }
      } else if (msg.type === 'enable-changed') {
        const meta = currentMeta()
        if (msg.account === currentAccount.value) {
          // 其他窗口停用/改了授权版本：本窗口必须切到同一口径
          if (msg.enabled === false) {
            data.value = null
            await loadData({ silent: true })
          } else if (msg.version && meta?.version !== msg.version) {
            await loadData({ silent: true })
          }
        }
      }
    }

    return {
      accounts, catalog, currentAccount, data, loading, error, lastFetchedVersion,
      currentMeta, loadCatalog, loadAccounts, selectAccount, loadData,
      saveConfig, disable, requestScoped, effectiveScopeOf, handleCrossTab,
    }
  })
