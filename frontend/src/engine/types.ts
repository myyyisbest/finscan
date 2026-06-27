export enum Verdict {
  PASS = 'PASS',
  WARN = 'WARN',
  FAIL = 'FAIL',
  SKIP = 'SKIP',
}

export enum RiskLevel {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  VERY_HIGH = 'VERY_HIGH',
  REJECT = 'REJECT',
}

export interface RuleContext {
  stock_code: string
  stock_name: string
  industry?: string

  audit_result?: string
  audit_agency?: string
  ann_date?: string
  end_date?: string

  income_list: any[]
  balance_list: any[]
  cashflow_list: any[]
  indicator_list: any[]

  peer_indicators: Record<string, any>
  pdf_data: Record<string, any>
}

export interface RuleResult {
  code: string
  name: string
  layer: number
  verdict: Verdict
  score_added: number
  detail: string
  raw_values: Record<string, any>
}

export interface ReportResult {
  stock_code: string
  stock_name: string
  report_year: number
  total_score: number
  risk_level: RiskLevel
  rule_results: RuleResult[]
  combo_bonus: number
  n_pass: number
  n_warn: number
  n_fail: number
  n_skip: number
}

export function latest(list: any[]): any | null {
  if (!list || list.length === 0) return null
  return list[0]
}

export function prev(list: any[], offset: number = 1): any | null {
  if (!list || list.length <= offset) return null
  return list[offset]
}

export function formatNumber(val: any, decimals: number = 2): string {
  if (val === null || val === undefined || val === '') return 'N/A'
  const num = Number(val)
  if (isNaN(num)) return String(val)
  return num.toFixed(decimals)
}
