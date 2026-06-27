import { RuleContext, ReportResult } from './types'
import { ruleEngine } from './rules'

export interface StockBasic {
  code: string
  name: string
  industry: string
  market: string
}

export const sampleStocks: StockBasic[] = [
  { code: '002475', name: '立讯精密', industry: '消费电子', market: 'SZ' },
  { code: '600519', name: '贵州茅台', industry: '白酒', market: 'SH' },
  { code: '300750', name: '宁德时代', industry: '动力电池', market: 'SZ' },
  { code: '601318', name: '中国平安', industry: '保险', market: 'SH' },
  { code: '000858', name: '五粮液', industry: '白酒', market: 'SZ' },
  { code: '002594', name: '比亚迪', industry: '新能源汽车', market: 'SZ' },
  { code: '600036', name: '招商银行', industry: '银行', market: 'SH' },
  { code: '300059', name: '东方财富', industry: '证券', market: 'SZ' },
  { code: '601012', name: '隆基绿能', industry: '光伏设备', market: 'SH' },
  { code: '000333', name: '美的集团', industry: '家电', market: 'SZ' },
]

function generateIncomeList(seed: number): any[] {
  const list: any[] = []
  for (let i = 0; i < 5; i++) {
    const year = 2024 - i
    const growth = 1 + (seed * 0.05 - i * 0.02)
    const revenue = 1000e8 * growth
    const netProfit = 100e8 * growth
    list.push({
      report_year: year,
      end_date: `${year}-12-31`,
      ann_date: `${year + 1}-03-15`,
      TOTAL_OPERATE_INCOME: revenue,
      OPERATE_INCOME: revenue * 0.98,
      revenue: revenue,
      oper_cost: revenue * (0.6 + seed * 0.05),
      sell_exp: revenue * 0.08,
      admin_exp: revenue * 0.05,
      fin_exp: revenue * 0.01,
      n_income_attr_p: netProfit,
      oth_biz_income: revenue * 0.02,
      assets_impair_loss: -netProfit * 0.01,
      credit_impa_loss: -netProfit * 0.005,
      audit_result: '标准无保留意见',
      audit_agency: '立信会计师事务所',
    })
  }
  return list
}

function generateBalanceList(seed: number): any[] {
  const list: any[] = []
  for (let i = 0; i < 5; i++) {
    const year = 2024 - i
    const growth = 1 + (seed * 0.08 - i * 0.03)
    const totalAssets = 2000e8 * growth
    list.push({
      report_year: year,
      total_assets: totalAssets,
      money_cap: totalAssets * 0.15,
      accounts_receiv: totalAssets * 0.12,
      accounts_payable: totalAssets * 0.08,
      inventory: totalAssets * 0.1,
      fix_assets: totalAssets * 0.2,
      cip: totalAssets * 0.03,
      st_borr: totalAssets * 0.05,
      lt_borr: totalAssets * 0.1,
      bond_payable: totalAssets * 0.05,
      lt_amort_deferred_exp: totalAssets * 0.005,
    })
  }
  return list
}

function generateCashflowList(seed: number): any[] {
  const list: any[] = []
  for (let i = 0; i < 5; i++) {
    const year = 2024 - i
    const growth = 1 + (seed * 0.06 - i * 0.02)
    const operCf = 150e8 * growth
    const invCf = -100e8 * growth
    list.push({
      report_year: year,
      n_cashflow_act: operCf,
      n_cashflow_inv_act: invCf,
      c_recp_prov_sg_act: 900e8 * growth,
      free_cashflow: operCf + invCf * 0.5,
    })
  }
  return list
}

function generateIndicatorList(seed: number): any[] {
  const list: any[] = []
  for (let i = 0; i < 5; i++) {
    const year = 2024 - i
    const gmBase = 25 + seed * 5
    list.push({
      report_year: year,
      grossprofit_margin: gmBase + i * 0.5,
      inv_turn: 5 + seed * 2 - i * 0.3,
      roe: 15 + seed * 3 - i * 0.5,
      roa: 8 + seed * 2 - i * 0.3,
      debt_to_assets: 50 - seed * 5 + i * 1,
      current_ratio: 1.5 + seed * 0.2 - i * 0.05,
    })
  }
  return list
}

export function buildMockContext(stock: StockBasic): RuleContext {
  const seed = stock.code.charCodeAt(stock.code.length - 1) % 10

  const incomeList = generateIncomeList(seed)
  const balanceList = generateBalanceList(seed)
  const cashflowList = generateCashflowList(seed)
  const indicatorList = generateIndicatorList(seed)

  const latestIncome = incomeList[0] || {}

  return {
    stock_code: stock.code,
    stock_name: stock.name,
    industry: stock.industry,
    audit_result: latestIncome.audit_result,
    audit_agency: latestIncome.audit_agency,
    ann_date: latestIncome.ann_date,
    end_date: latestIncome.end_date,
    income_list: incomeList,
    balance_list: balanceList,
    cashflow_list: cashflowList,
    indicator_list: indicatorList,
    peer_indicators: {
      grossprofit_margin_median: 25 + seed * 2,
      bad_debt_ratio_median: 1.5,
    },
    pdf_data: {},
  }
}

export function analyzeLocal(stock: StockBasic): ReportResult {
  const ctx = buildMockContext(stock)
  return ruleEngine.analyze(ctx, 2024)
}

export function searchStocks(keyword: string): StockBasic[] {
  if (!keyword) return sampleStocks
  const kw = keyword.toLowerCase()
  return sampleStocks.filter(s =>
    s.code.includes(kw) || s.name.toLowerCase().includes(kw)
  )
}
