import axios, { AxiosInstance, AxiosError } from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

// Vite 开发模式：通过 3000 端口代理 /api 到 8000
// 生产模式：前端由后端提供，API 走同域名
// 统一使用相对路径

const api: AxiosInstance = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => {
    return response
  },
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status
      const data = error.response.data as any
      
      if (status === 3001 || (data && data.code === 3001)) {
        const authStore = useAuthStore()
        authStore.setToken(null)
        authStore.userInfo = null
        router.push('/login')
      }
    }
    return Promise.reject(error)
  }
)

export const get = <T = any>(url: string, params?: any, config?: any): Promise<{ data: T }> => {
  return api.get(url, { params, ...config })
}

export const post = <T = any>(url: string, data?: any, config?: any): Promise<{ data: T }> => {
  return api.post(url, data, config)
}

export const put = <T = any>(url: string, data?: any, config?: any): Promise<{ data: T }> => {
  return api.put(url, data, config)
}

export const del = <T = any>(url: string, params?: any, config?: any): Promise<{ data: T }> => {
  return api.delete(url, { params, ...config })
}

export default api
