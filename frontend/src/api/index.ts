import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { AccountInfo, Scope, ScreenData } from '@/types'

// 令牌仅存 sessionStorage：同一账号每个窗口独立登录，窗口之间互不串号；
// 已发布的授权版本 + 服务端确定性数据保证各窗口看到的取值口径一致。
const TOKEN_KEY = 'lad_token'

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}
export function setToken(token: string) {
  sessionStorage.setItem(TOKEN_KEY, token)
}
export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY)
}

export const http = axios.create({ baseURL: '/' })

http.interceptors.request.use((cfg) => {
  const token = getToken()
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

http.interceptors.response.use(
  (resp) => resp,
  (error) => {
    // 统一把后端的拒绝原因抛给调用方展示（401/403/409/422 均写明原因）
    const detail = error?.response?.data?.detail
    const reason = typeof detail === 'string'
      ? detail
      : (detail?.reason ? [detail.reason, ...(detail.errors || [])].join('\n') : undefined)
    return Promise.reject(Object.assign(error, { reason: reason || error.message }))
  }
)

export async function login(username: string, password: string) {
  const { data } = await http.post('/api/login', { username, password })
  setToken(data.token)
  return data
}

export async function fetchMe(): Promise<AccountInfo> {
  const { data } = await http.get('/api/me')
  return data
}

export async function fetchAllScopes(): Promise<{
  accounts: string[]
  scopes: Record<string, Scope>
  resourceCatalog: { sources: string[]; panels: string[] }
}> {
  const { data } = await http.get('/api/scopes')
  return data
}

export async function publishScope(
  username: string, entries: { resource: string; effect: 'allow' | 'deny' }[],
  expectVersion?: number
): Promise<{ message: string; scope: Scope }> {
  const { data } = await http.put(`/api/scopes/${username}`, {
    entries, enabled: true, expectVersion: expectVersion ?? null
  })
  return { message: data.message, scope: data.scope }
}

export async function setScopeEnabled(username: string, enabled: boolean) {
  const { data } = await http.put(`/api/scopes/${username}`, { entries: [], enabled })
  return data
}

export async function fetchScreenData(type: string, version?: number): Promise<ScreenData> {
  const { data } = await http.post('/api/screen/data', { type, version: version ?? null })
  return data
}

export { ElMessage }
