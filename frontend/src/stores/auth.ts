import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as apiLogin, register as apiRegister, getMe as apiGetMe } from '@/api/auth'
import type { UserInfo } from '@/types'

const TOKEN_KEY = 'finscan_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const userInfo = ref<UserInfo | null>(null)
  const loading = ref(false)

  function setToken(newToken: string | null) {
    token.value = newToken
    if (newToken) {
      localStorage.setItem(TOKEN_KEY, newToken)
    } else {
      localStorage.removeItem(TOKEN_KEY)
    }
  }

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const response = await apiLogin({ username, password })
      if (response.data.data.token) {
        setToken(response.data.data.token)
        await fetchMe()
      }
      return response
    } finally {
      loading.value = false
    }
  }

  async function register(username: string, password: string, email?: string) {
    loading.value = true
    try {
      return await apiRegister({ username, password, email })
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    if (!token.value) return
    loading.value = true
    try {
      const response = await apiGetMe()
      userInfo.value = response.data.data
    } catch {
      setToken(null)
    } finally {
      loading.value = false
    }
  }

  function logout() {
    setToken(null)
    userInfo.value = null
  }

  return {
    token,
    userInfo,
    loading,
    login,
    register,
    fetchMe,
    logout,
    setToken
  }
})
