import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as apiLogin, fetchMe, clearToken, getToken } from '@/api'
import type { AccountInfo } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const account = ref<AccountInfo | null>(null)
  const ready = ref(false)

  async function restore() {
    ready.value = false
    if (getToken()) {
      try { account.value = await fetchMe() } catch { clearToken(); account.value = null }
    }
    ready.value = true
  }

  async function login(username: string, password: string) {
    await apiLogin(username, password)
    account.value = await fetchMe()
  }

  async function refreshMe() {
    account.value = await fetchMe()
  }

  function logout() {
    clearToken()
    account.value = null
  }

  return { account, ready, restore, login, refreshMe, logout }
})
