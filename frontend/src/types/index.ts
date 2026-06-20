export interface ApiResponse<T> {
  code: number
  message: string
  data: T
  timestamp: number
}

export interface PageData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface StockSearchItem {
  stock_code: string
  stock_name: string
  industry: string | null
  market: string | null
  is_st: boolean
}

export interface StockBasic {
  stock_code: string
  stock_name: string
  industry: string | null
  market: string | null
  is_st: boolean
  list_date: string | null
  main_business: string | null
}

export interface StockOverview {
  basic: StockBasic
  latest_annual: {
    report_date: string
    report_type: string
    revenue: number | null
    net_profit: number | null
    total_assets: number | null
    total_liabilities: number | null
    equity: number | null
    roe: number | null
    roa: number | null
    gross_margin: number | null
    net_margin: number | null
    debt_to_assets: number | null
    current_ratio: number | null
    quick_ratio: number | null
  } | null
}

export interface FinIndicator {
  report_date: string
  report_type: string
  roe: string | null
  roa: string | null
  gross_margin: string | null
  net_margin: string | null
  debt_to_assets: string | null
  current_ratio: string | null
  quick_ratio: string | null
  inventory_turnover: string | null
  total_asset_turnover: string | null
  net_profit_margin: string | null
  operating_profit_margin: string | null
  eps: string | null
  bps: string | null
  dps: string | null
  peg: string | null
}

export interface BalanceSheetItem {
  report_date: string
  report_type: string
  item_name: string
  value: number | null
  unit: string
}

export interface IncomeStatementItem {
  report_date: string
  report_type: string
  item_name: string
  value: number | null
  unit: string
}

export interface CashFlowItem {
  report_date: string
  report_type: string
  item_name: string
  value: number | null
  unit: string
}

export interface WatchlistGroup {
  group_name: string
  stocks: WatchlistItem[]
}

export interface WatchlistItem {
  id: number
  stock_code: string
  stock_name: string
  remark: string | null
  add_time: string
}

export interface UserInfo {
  user_id: number
  username: string
  email: string | null
  is_active: boolean
}

export interface RiskAssessment {
  stock_code: string
  stock_name: string
  report_date: string
  risk_level: 'low' | 'medium' | 'high' | 'very_high' | 'excluded'
  total_score: number
  rules: {
    rule_name: string
    passed: boolean
    score: number
    detail: string
  }[]
}

export interface Announcement {
  id: number
  title: string
  ann_type: string
  disclosure_date: string
  is_risk: boolean
  content: string | null
  stock_code: string | null
  stock_name: string | null
}
