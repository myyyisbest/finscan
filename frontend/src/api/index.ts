import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' }
})

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
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const get = (url: string, params?: any) => api.get(url, { params })
export const post = (url: string, data?: any) => api.post(url, data)
export const put = (url: string, data?: any) => api.put(url, data)
export const del = (url: string, params?: any) => api.delete(url, { params })

export default api
