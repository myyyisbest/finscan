import { get, post } from './index'
import type { ApiResponse, UserInfo } from '@/types'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  user: UserInfo
}

export interface RegisterRequest {
  username: string
  password: string
  email?: string
}

export const login = (data: LoginRequest) => {
  return post<ApiResponse<LoginResponse>>('/api/v1/auth/login', data)
}

export const register = (data: RegisterRequest) => {
  return post<ApiResponse<any>>('/api/v1/auth/register', data)
}

export const getMe = () => {
  return get<ApiResponse<UserInfo>>('/api/v1/auth/me')
}
