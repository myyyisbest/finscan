import api from './index'

export interface LoginRequest {
  username: string
  password: string
}

export interface UserInfo {
  id: number
  username: string
  is_admin: boolean
}

export interface LoginResponse {
  code: number
  data: {
    access_token: string
    token_type: string
    user_id: number
    username: string
    is_admin: boolean
  }
}

export const authApi = {
  login: (username: string, password: string) =>
    api.post<LoginResponse>('/api/v1/auth/login', { username, password }),

  guest: () =>
    api.post<LoginResponse>('/api/v1/auth/guest'),
}
