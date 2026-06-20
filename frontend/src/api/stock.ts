import { get } from './index'
import type { ApiResponse, PageData, StockSearchItem, StockOverview, FinIndicator, BalanceSheetItem, IncomeStatementItem, CashFlowItem } from '@/types'

export const searchStocks = (params: { keyword?: string; page?: number; page_size?: number }) => {
  return get<ApiResponse<PageData<StockSearchItem>>>('/api/v1/stocks/search', params)
}

export const getStockBasic = (code: string) => {
  return get<ApiResponse<any>>(`/api/v1/stocks/${code}/basic`)
}

export const getStockOverview = (code: string) => {
  return get<ApiResponse<StockOverview>>(`/api/v1/stocks/${code}/overview`)
}

export const getBalanceSheet = (code: string, params?: { report_type?: string; page?: number; page_size?: number }) => {
  return get<ApiResponse<PageData<BalanceSheetItem>>>(`/api/v1/stocks/${code}/balance-sheet`, params)
}

export const getIncomeStatement = (code: string, params?: { report_type?: string; page?: number; page_size?: number }) => {
  return get<ApiResponse<PageData<IncomeStatementItem>>>(`/api/v1/stocks/${code}/income-statement`, params)
}

export const getCashFlow = (code: string, params?: { report_type?: string; page?: number; page_size?: number }) => {
  return get<ApiResponse<PageData<CashFlowItem>>>(`/api/v1/stocks/${code}/cash-flow`, params)
}

export const getIndicators = (code: string, params?: { page?: number; page_size?: number }) => {
  return get<ApiResponse<PageData<FinIndicator>>>(`/api/v1/stocks/${code}/indicators`, params)
}

export const getRiskAssessment = (code: string, params?: { report_date?: string }) => {
  return get<ApiResponse<any>>(`/api/v1/stocks/${code}/risk-assessment`, params)
}
