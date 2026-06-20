import axios, { AxiosInstance, AxiosError } from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

// 动态 baseURL：预览环境需要使用后端服务的网络地址
const getBaseURL = () => {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    // 预览环境：使用后端服务的网络地址
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      // 尝试使用同域名的 8000 端口（如果后端在同一网络）
      return `http://10.59.26.252:8000`
    }
  }
  return 'http://localhost:8000'
}

const api: AxiosInstance = axios.create({
  baseURL: getBaseURL(),
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
