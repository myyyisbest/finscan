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

export const getFinancialAnnual = (code: string, year: string) => {
  return Promise.all([
    getBalanceSheet(code, { report_type: 'Annual', page: 1, page_size: 1 }),
    getIncomeStatement(code, { report_type: 'Annual', page: 1, page_size: 1 }),
    getCashFlow(code, { report_type: 'Annual', page: 1, page_size: 1 }),
  ])
}

export const getFinancialQuarter = (code: string, period: string) => {
  const rt = period // e.g. "Q1", "Q2", "Q3", "Annual"
  return Promise.all([
    getBalanceSheet(code, { report_type: rt, page: 1, page_size: 1 }),
    getIncomeStatement(code, { report_type: rt, page: 1, page_size: 1 }),
    getCashFlow(code, { report_type: rt, page: 1, page_size: 1 }),
  ])
}

export const getRiskAssessment = (code: string, params?: { report_date?: string }) => {
  return get<ApiResponse<any>>(`/api/v1/stocks/${code}/risk-assessment`, params)
}
