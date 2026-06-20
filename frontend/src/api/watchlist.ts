import { get, post, put, del } from './index'
import type { ApiResponse, WatchlistGroup } from '@/types'

export const getWatchlistGroups = () => {
  return get<ApiResponse<WatchlistGroup[]>>('/api/v1/watchlist/groups')
}

export const addToWatchlist = (data: { stock_code: string; stock_name: string; group_name: string; remark?: string }) => {
  return post<ApiResponse<any>>('/api/v1/watchlist/add', data)
}

export const removeFromWatchlist = (data: { stock_code: string; group_name: string }) => {
  return del<ApiResponse<any>>('/api/v1/watchlist/remove', data)
}

export const renameGroup = (data: { old_name: string; new_name: string }) => {
  return put<ApiResponse<any>>('/api/v1/watchlist/group/rename', data)
}

export const moveStock = (data: { stock_code: string; from_group: string; to_group: string }) => {
  return put<ApiResponse<any>>('/api/v1/watchlist/move', data)
}

export const createGroup = (data: { group_name: string }) => {
  return post<ApiResponse<any>>('/api/v1/watchlist/group/create', data)
}

export const deleteGroup = (data: { group_name: string }) => {
  return del<ApiResponse<any>>('/api/v1/watchlist/group/delete', data)
}
