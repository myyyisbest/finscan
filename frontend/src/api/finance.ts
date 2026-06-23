import api from './index'

export interface StockInfo {
  stock_code: string
  stock_name: string
  market: string
  secucode: string
  industry?: string
  full_name?: string
  list_date?: string
  is_st: boolean
  latest_report?: {
    report_date?: string
    report_name?: string
    total_revenue?: number
    net_profit_parent?: number
    roe?: number
    debt_ratio?: number
  }
}

export interface SearchResult {
  stock_code: string
  stock_name: string
  market: string
  secucode: string
  industry?: string
}

export interface WatchlistItem {
  stock_code: string
  stock_name: string
  market: string
  secucode: string
  industry?: string
  remark?: string
  add_time: string
  latest_report?: {
    report_date?: string
    report_name?: string
    total_revenue?: number
    net_profit_parent?: number
    roe?: number
    debt_ratio?: number
    revenue_yoy?: number
  }
}

export interface ReportDate {
  report_date: string
  report_name: string
  report_type: string
  notice_date?: string
}

export interface FinIndicatorSection {
  name: string
  items: Array<{
    name: string
    key: string
    values: (number | null)[]
  }>
}

export interface MainIndicatorsData {
  report_dates: string[]
  report_names: string[]
  sections: FinIndicatorSection[]
}

export interface FinTableSection {
  name: string
  items: Array<{
    name: string
    key: string
    values: (number | null | string)[]
  }>
}

export interface FinTableData {
  report_dates: string[]
  report_names: string[]
  view: string
  sections: FinTableSection[]
}

export const stockApi = {
  search: (keyword: string) =>
    api.get<{ code: number; data: SearchResult[] }>(`/api/v1/stock/search?keyword=${encodeURIComponent(keyword)}`),

  getInfo: (code: string) =>
    api.get<{ code: number; data: StockInfo }>(`/api/v1/stock/${code}`),

  getReportDates: (code: string, reportType?: string, limit = 20) =>
    api.get<{ code: number; data: ReportDate[] }>(
      `/api/v1/stock/${code}/reports/dates?limit=${limit}${reportType ? `&report_type=${reportType}` : ''}`
    ),
}

export const financeApi = {
  getMainIndicators: (code: string, view = 'report', quarters = 8) =>
    api.get<{ code: number; data: MainIndicatorsData }>(
      `/api/v1/finance/${code}/main-indicators?view=${view}&quarters=${quarters}`
    ),

  getBalanceSheet: (code: string, view = 'report', quarters = 8, reportType?: string) =>
    api.get<{ code: number; data: FinTableData }>(
      `/api/v1/finance/${code}/balance-sheet?view=${view}&quarters=${quarters}${reportType ? `&report_type=${reportType}` : ''}`
    ),

  getIncomeStatement: (code: string, view = 'report', quarters = 8, reportType?: string) =>
    api.get<{ code: number; data: FinTableData }>(
      `/api/v1/finance/${code}/income-statement?view=${view}&quarters=${quarters}${reportType ? `&report_type=${reportType}` : ''}`
    ),

  getCashFlow: (code: string, view = 'report', quarters = 8, reportType?: string) =>
    api.get<{ code: number; data: FinTableData }>(
      `/api/v1/finance/${code}/cash-flow?view=${view}&quarters=${quarters}${reportType ? `&report_type=${reportType}` : ''}`
    ),
}

export const watchlistApi = {
  list: () => api.get<{ code: number; data: WatchlistItem[] }>('/api/v1/watchlist'),
  add: (stock_code: string, stock_name?: string, remark?: string) =>
    api.post<{ code: number; data: any }>('/api/v1/watchlist', { stock_code, stock_name, remark }),
  remove: (code: string) => api.delete<{ code: number; data: any }>(`/api/v1/watchlist/${code}`),
}

export const collectorApi = {
  triggerCollect: (scope: 'watchlist' | 'single' = 'watchlist', stock_code?: string) =>
    api.post<{ code: number; data: any }>('/api/v1/collector/trigger', { scope, stock_code }),
  getStatus: (code: string) => api.get<{ code: number; data: any }>(`/api/v1/collector/status/${code}`),
}
