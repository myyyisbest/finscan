import axios from 'axios'

// 获取API基础地址：优先使用localStorage配置，移动端APP需要配置后端地址
function getBaseURL(): string {
  // Capacitor环境检测
  const isCapacitor = (window as any).Capacitor !== undefined
  if (isCapacitor) {
    const saved = localStorage.getItem('api_base_url')
    if (saved) return saved
    // 默认提示用户配置
    return ''
  }
  // Web环境使用相对路径（走vite代理或同源部署）
  return ''
}

const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' }
})

// 提供更新baseURL的方法
export function updateBaseURL(url: string) {
  localStorage.setItem('api_base_url', url)
  api.defaults.baseURL = url
}

// 初始化：如果有保存的配置，使用它
const savedURL = localStorage.getItem('api_base_url')
if (savedURL) {
  api.defaults.baseURL = savedURL
}

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (config.method === 'get' && config.params) {
    const encodedParams: Record<string, string> = {}
    for (const key of Object.keys(config.params)) {
      const val = config.params[key]
      if (val !== undefined && val !== null && val !== '') {
        encodedParams[key] = encodeURIComponent(encodeURIComponent(String(val)))
      }
    }
    config.params = encodedParams
    config.paramsSerializer = (params: any) => {
      return Object.entries(params)
        .map(([k, v]) => `${k}=${v}`)
        .join('&')
    }
  }
  return config
})

api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      // Capacitor环境下不跳转，用路由
      if (!(window as any).Capacitor) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const get = (url: string, params?: any) => api.get(url, { params })
export const post = (url: string, data?: any) => api.post(url, data)
export const put = (url: string, data?: any) => api.put(url, data)
export const del = (url: string, params?: any) => api.delete(url, { params })

export default api
