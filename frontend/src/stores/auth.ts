import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const username = ref<string>(localStorage.getItem('username') || '')
  const userId = ref<number>(parseInt(localStorage.getItem('user_id') || '0'))
  const isAdmin = ref<boolean>(localStorage.getItem('is_admin') === 'true')

  async function login(user: string, pwd: string) {
    const res = await authApi.login(user, pwd)
    if (res.code === 0 && res.data) {
      token.value = res.data.access_token
      username.value = res.data.username
      userId.value = res.data.user_id
      isAdmin.value = res.data.is_admin
      localStorage.setItem('token', res.data.access_token)
      localStorage.setItem('username', res.data.username)
      localStorage.setItem('user_id', String(res.data.user_id))
      localStorage.setItem('is_admin', String(res.data.is_admin))
      return true
    }
    return false
  }

  function logout() {
    token.value = null
    username.value = ''
    userId.value = 0
    isAdmin.value = false
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('user_id')
    localStorage.removeItem('is_admin')
  }

  return { token, username, userId, isAdmin, login, logout }
})
