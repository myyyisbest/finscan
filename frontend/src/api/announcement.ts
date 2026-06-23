import { get, post, del, put } from './index'
import type { ApiResponse, PageData } from '@/types'

export interface AnnouncementItem {
  id: number
  stock_code: string
  ann_title: string
  ann_type: string
  publish_date: string
  is_risk: boolean
  pdf_url: string | null
  content_summary: string | null
}

export const getAnnouncements = (params?: {
  stock_code?: string
  ann_type?: string
  is_risk?: boolean
  keyword?: string
  page?: number
  page_size?: number
}) => {
  return get<ApiResponse<PageData<AnnouncementItem>>>('/api/v1/announcements/', params)
}

export const getAnnouncementDetail = (id: number) => {
  return get<ApiResponse<AnnouncementItem>>(`/api/v1/announcements/${id}`)
}
