import {
  Verdict,
  RiskLevel,
  RuleContext,
  RuleResult,
  ReportResult,
  latest,
  prev,
  formatNumber,
} from './types'

// ==================== 规则基类 ====================
abstract class BaseRule {
  abstract code: string
  abstract name: string
  abstract layer: number
  weight_warn: number = 0
  weight_fail: number = 0

  abstract evaluate(ctx: RuleContext): RuleResult

  protected makeResult(
    verdict: Verdict,
    score: number,
    detail: string,
    rawValues: Record<string, any> = {}
  ): RuleResult {
    return {
      code: this.code,
      name: this.name,
      layer: this.layer,
      verdict,
      score_added: score,
      detail,
      raw_values: rawValues,
    }
  }

  protected skip(detail: string): RuleResult {
    return this.makeResult(Verdict.SKIP, 0, detail)
  }

  protected pass(detail: string, rawValues?: Record<string, any>): RuleResult {
    return this.makeResult(Verdict.PASS, 0, detail + ' → PASS', rawValues)
  }

  protected warn(detail: string, rawValues?: Record<string, any>): RuleResult {
    return this.makeResult(Verdict.WARN, this.weight_warn, detail + ' → WARN', rawValues)
  }

  protected fail(detail: string, rawValues?: Record<string, any>): RuleResult {
    return this.makeResult(Verdict.FAIL, this.weight_fail, detail + ' → FAIL', rawValues)
  }
}

// ==================== Layer 0: 门槛检查 ====================

class Rule0_1 extends BaseRule {
  code = '0.1'
  name = '审计意见'
  layer = 0
  weight_fail = 999

  evaluate(ctx: RuleContext): RuleResult {
    const result = ctx.audit_result || ''
    const detail = `审计意见: ${result || '无数据'}`

    if (!result) {
      return this.skip('无审计数据')
    }

    const nonStandard = [
      '保留意见', '无法表示意见', '否定意见',
      '带强调事项段的无保留', '带强调事项段',
    ].some(kw => result.includes(kw))

    const isStandard = ['标准无保留', '标准的无保留'].some(kw => result.includes(kw))

    if (nonStandard && !isStandard) {
      return this.makeResult(Verdict.FAIL, 999, detail + ' → 非标准意见，一票否决', { audit_result: result })
    }
    return this.pass(detail, { audit_result: result })
  }
}

class Rule0_2 extends BaseRule {
  code = '0.2'
  name = '按时披露'
  layer = 0
  weight_fail = 999

  evaluate(ctx: RuleContext): RuleResult {
    if (!ctx.ann_date || !ctx.end_date) {
      return this.skip('无披露日期数据')
    }

    try {
      const endDt = new Date(ctx.end_date)
      const annDt = new Date(ctx.ann_date)
      const deadline = new Date(endDt.getFullYear() + 1, 3, 30)

      const detail = `报告期: ${ctx.end_date}, 披露日期: ${ctx.ann_date}, 截止日期: ${deadline.toISOString().slice(0, 10)}`

      if (annDt <= deadline) {
        const daysDiff = Math.floor((deadline.getTime() - annDt.getTime()) / (1000 * 60 * 60 * 24))
        return this.pass(detail + ` → 提前${daysDiff}天披露`)
      } else {
        const daysDiff = Math.floor((annDt.getTime() - deadline.getTime()) / (1000 * 60 * 60 * 24))
        return this.makeResult(Verdict.FAIL, 999, detail + ` → 超期${daysDiff}天披露`)
      }
    } catch {
      return this.skip('日期格式错误')
    }
  }
}

// ==================== Layer 1: 利润表信号 ====================

class Rule1_1 extends BaseRule {
  code = '1.1'
  name = '毛利率异常'
  layer = 1
  weight_warn = 2
  weight_fail = 5

  evaluate(ctx: RuleContext): RuleResult {
    const cur = latest(ctx.indicator_list)
    const p = prev(ctx.indicator_list)

    if (!cur || cur.grossprofit_margin === null || cur.grossprofit_margin === undefined) {
      return this.skip('无毛利率数据')
    }

    const gmCur = Number(cur.grossprofit_margin || 0)
    const gmPrev = p ? Number(p.grossprofit_margin || gmCur) : gmCur
    const gmYoy = gmCur - gmPrev

    const peerGm = Number(ctx.peer_indicators.grossprofit_margin_median || 0)
    const gmVsPeer = peerGm ? gmCur - peerGm : 0

    let detail = `当前毛利率: ${formatNumber(gmCur, 2)}%, YoY: ${formatNumber(gmYoy, 2)}pp`
    if (peerGm) {
      detail += `, 同行中位数: ${formatNumber(peerGm, 2)}%, vs同行: ${formatNumber(gmVsPeer, 2)}pp`
    }

    if (Math.abs(gmYoy) > 10 && gmVsPeer > 15) {
      return this.fail(detail + ' → 大幅波动且远超同行', { gm_cur: gmCur, gm_yoy: gmYoy, gm_vs_peer: gmVsPeer })
    } else if (Math.abs(gmYoy) > 5 || gmVsPeer > 15) {
      return this.warn(detail + ' → 波动较大或超出同行', { gm_cur: gmCur, gm_yoy: gmYoy, gm_vs_peer: gmVsPeer })
    }
    return this.pass(detail, { gm_cur: gmCur, gm_yoy: gmYoy, gm_vs_peer: gmVsPeer })
  }
}

class Rule1_2 extends BaseRule {
  code = '1.2'
  name = '营收虚增信号'
  layer = 1
  weight_warn = 2
  weight_fail = 5

  evaluate(ctx: RuleContext): RuleResult {
    const indCur = latest(ctx.indicator_list)
    const indPrev = prev(ctx.indicator_list)
    const balCur = latest(ctx.balance_list)
    const balPrev = prev(ctx.balance_list)
    const incCur = latest(ctx.income_list)
    const incPrev = prev(ctx.income_list)

    const signals: string[] = []

    if (indCur && indPrev) {
      const gmCur = indCur.grossprofit_margin
      const gmPrev = indPrev.grossprofit_margin
      if (gmCur !== null && gmCur !== undefined && gmPrev !== null && gmPrev !== undefined && Number(gmCur) > Number(gmPrev)) {
        signals.push('A')
      }
    }

    if (balCur && balPrev && incCur && incPrev) {
      const arCur = Number(balCur.accounts_receiv || 0)
      const arPrev = Number(balPrev.accounts_receiv || 0)
      const revCur = Number(incCur.revenue || 0)
      const revPrev = Number(incPrev.revenue || 0)

      if (revCur > 0 && revPrev > 0) {
        const arGrowth = arPrev ? (arCur - arPrev) / arPrev * 100 : 0
        const revGrowth = revPrev ? (revCur - revPrev) / revPrev * 100 : 0
        if (arGrowth > revGrowth) {
          signals.push('B')
        }
      }
    }

    if (balCur && balPrev) {
      const apCur = Number(balCur.accounts_payable || 0)
      const apPrev = Number(balPrev.accounts_payable || 0)
      if (apCur < apPrev) {
        signals.push('C')
      }
    }

    const nSignals = signals.length
    const detail = `信号: A(毛利率↑)=${signals.includes('A')}, B(应收↑>营收↑)=${signals.includes('B')}, C(应付↓)=${signals.includes('C')}`

    if (nSignals >= 3) {
      return this.fail(detail + ' → 三信号叠加，高度可疑', { signals, n_signals: nSignals })
    } else if (nSignals === 2) {
      return this.warn(detail + ' → 满足2个条件', { signals, n_signals: nSignals })
    }
    return this.pass(detail, { signals, n_signals: nSignals })
  }
}

class Rule1_3 extends BaseRule {
  code = '1.3'
  name = '运费增速异常'
  layer = 1
  weight_warn = 2
  weight_fail = 5

  evaluate(ctx: RuleContext): RuleResult {
    const freightGrowth = ctx.pdf_data.freight_growth
    const revenueYoy = ctx.pdf_data.revenue_yoy

    if (freightGrowth === undefined || freightGrowth === null) {
      return this.skip('PDF中未找到运费明细')
    }

    const detail = `运费增速: ${formatNumber(freightGrowth, 1)}%, 营收增速: ${formatNumber(revenueYoy, 1)}%`
    const threshold = revenueYoy ? revenueYoy * 0.25 : 0

    if (Number(freightGrowth) < threshold) {
      return this.fail(detail + ' → 运费增速远低于营收增速')
    } else if (Number(freightGrowth) < Number(revenueYoy || 0) * 0.5) {
      return this.warn(detail + ' → 运费增速偏低')
    }
    return this.pass(detail)
  }
}

class Rule1_4 extends BaseRule {
  code = '1.4'
  name = '其他业务收入异常'
  layer = 1
  weight_warn = 2
  weight_fail = 5

  evaluate(ctx: RuleContext): RuleResult {
    const incCur = latest(ctx.income_list)
    const incPrev = prev(ctx.income_list)

    if (!incCur) {
      return this.skip('无利润表数据')
    }

    const othIncome = Number(incCur.oth_biz_income || 0)
    const revenue = Number(incCur.revenue || 1)
    const ratio = revenue ? othIncome / revenue * 100 : 0

    let ratioPrev = 0
    if (incPrev) {
      const othIncomePrev = Number(incPrev.oth_biz_income || 0)
      const revenuePrev = Number(incPrev.revenue || 1)
      ratioPrev = revenuePrev ? othIncomePrev / revenuePrev * 100 : 0
    }

    const ratioChange = ratio - ratioPrev
    const detail = `其他业务收入占比: ${formatNumber(ratio, 2)}%, 同比变化: ${formatNumber(ratioChange, 2)}pp`

    if (ratio > 15 || ratioChange > 10) {
      return this.fail(detail + ' → 占比异常高', { ratio, ratio_prev: ratioPrev, ratio_change: ratioChange })
    } else if (ratio > 5 && ratioChange > 3) {
      return this.warn(detail + ' → 占比和变化较大', { ratio, ratio_prev: ratioPrev, ratio_change: ratioChange })
    }
    return this.pass(detail, { ratio, ratio_prev: ratioPrev, ratio_change: ratioChange })
  }
}

class Rule1_5 extends BaseRule {
  code = '1.5'
  name = '费用率异常下降'
  layer = 1
  weight_warn = 2
  weight_fail = 5

  evaluate(ctx: RuleContext): RuleResult {
    if (ctx.income_list.length < 3) {
      return this.skip('数据不足3年')
    }

    const ratios: number[] = []
    for (const inc of ctx.income_list.slice(0, 3)) {
      const sell = Number(inc.sell_exp || 0)
      const admin = Number(inc.admin_exp || 0)
      const fin = Number(inc.fin_exp || 0)
      const rev = Number(inc.revenue || 1)
      if (rev > 0) {
        ratios.push((sell + admin + fin) / rev * 100)
      }
    }

    if (ratios.length < 2) {
      return this.skip('数据不足')
    }

    const avg3yr = ratios.length > 1 ? ratios.slice(1).reduce((a, b) => a + b, 0) / (ratios.length - 1) : ratios[0]
    const currentRatio = ratios[0]
    const drop = avg3yr - currentRatio

    const detail = `当前费用率: ${formatNumber(currentRatio, 2)}%, 近3年均值: ${formatNumber(avg3yr, 2)}%, 下降: ${formatNumber(drop, 2)}pp`

    if (drop > 5) {
      return this.fail(detail + ' → 费用率大幅下降', { current_ratio: currentRatio, avg_3yr: avg3yr, drop })
    } else if (drop > 3) {
      return this.warn(detail + ' → 费用率下降明显', { current_ratio: currentRatio, avg_3yr: avg3yr, drop })
    }
    return this.pass(detail, { current_ratio: currentRatio, avg_3yr: avg3yr, drop })
  }
}

class Rule1_6 extends BaseRule {
  code = '1.6'
  name = '资产减值暴增'
  layer = 1
  weight_warn = 2
  weight_fail = 5

  evaluate(ctx: RuleContext): RuleResult {
    const incCur = latest(ctx.income_list)
    const incPrev = prev(ctx.income_list)

    if (!incCur) {
      return this.skip('无利润表数据')
    }

    const impairCur = Math.abs(Number(incCur.assets_impair_loss || 0))
    const creditCur = Math.abs(Number(incCur.credit_impa_loss || 0))
    const totalImpair = impairCur + creditCur
    const netProfit = Number(incCur.n_income_attr_p || 0)

    if (totalImpair === 0) {
      return this.pass('无减值损失')
    }

    let impairPrev = 0
    if (incPrev) {
      impairPrev = Math.abs(Number(incPrev.assets_impair_loss || 0)) + Math.abs(Number(incPrev.credit_impa_loss || 0))
    }

    const impairYoy = impairPrev ? ((totalImpair - impairPrev) / impairPrev * 100) : 999
    const impairToProfit = netProfit ? (totalImpair / Math.abs(netProfit) * 100) : 0

    const detail = `减值损失: ${formatNumber(totalImpair / 1e8, 2)}亿, YoY: ${formatNumber(impairYoy, 1)}%, 占净利润: ${formatNumber(impairToProfit, 1)}%`

    if (impairYoy > 100 || impairToProfit > 5) {
      return this.fail(detail, { total_impair: totalImpair, impair_yoy: impairYoy, impair_to_profit: impairToProfit })
    } else if (impairYoy > 50) {
      return this.warn(detail, { total_impair: totalImpair, impair_yoy: impairYoy, impair_to_profit: impairToProfit })
    }
    return this.pass(detail, { total_impair: totalImpair, impair_yoy: impairYoy, impair_to_profit: impairToProfit })
  }
}

// ==================== Layer 2: 现金流量表信号 ====================

class Rule2_1 extends BaseRule {
  code = '2.1'
  name = '投资支出异常'
  layer = 2
  weight_warn = 3
  weight_fail = 6

  evaluate(ctx: RuleContext): RuleResult {
    if (ctx.cashflow_list.length < 4) {
      return this.skip('数据不足4年')
    }

    let years = 0
    for (const cf of ctx.cashflow_list.slice(0, 5)) {
      const operCf = Number(cf.n_cashflow_act || 0)
      const invCf = Number(cf.n_cashflow_inv_act || 0)
      if (operCf > 0 && Math.abs(invCf) > operCf * 0.8) {
        years++
      }
    }

    const detail = `连续多年经营CF良好但大额投资支出: ${years}/5年`

    if (years >= 4) {
      return this.fail(detail + ' → 多年投资无效', { years })
    } else if (years >= 2) {
      return this.warn(detail, { years })
    }
    return this.pass(detail, { years })
  }
}

class Rule2_2 extends BaseRule {
  code = '2.2'
  name = '经营现金流为负'
  layer = 2
  weight_warn = 3
  weight_fail = 6

  evaluate(ctx: RuleContext): RuleResult {
    if (ctx.cashflow_list.length < 3) {
      return this.skip('数据不足3年')
    }

    let negYears = 0
    let consecutive = 0
    let maxConsecutive = 0

    for (const cf of ctx.cashflow_list.slice(0, 5)) {
      const operCf = Number(cf.n_cashflow_act || 0)
      if (operCf < 0) {
        negYears++
        consecutive++
        maxConsecutive = Math.max(maxConsecutive, consecutive)
      } else {
        consecutive = 0
      }
    }

    const detail = `近5年经营CF为负: ${negYears}年, 连续最长: ${maxConsecutive}年`

    if (maxConsecutive >= 3) {
      return this.fail(detail + ' → 连续亏损', { neg_years: negYears, max_consecutive: maxConsecutive })
    } else if (negYears >= 2) {
      return this.warn(detail, { neg_years: negYears, max_consecutive: maxConsecutive })
    }
    return this.pass(detail, { neg_years: negYears, max_consecutive: maxConsecutive })
  }
}

class Rule2_3 extends BaseRule {
  code = '2.3'
  name = '大存大贷'
  layer = 2
  weight_warn = 3
  weight_fail = 6

  evaluate(ctx: RuleContext): RuleResult {
    const bal = latest(ctx.balance_list)
    const incCur = latest(ctx.income_list)

    if (!bal) {
      return this.skip('无资产负债表数据')
    }

    const cash = Number(bal.money_cap || 0)
    const stBorr = Number(bal.st_borr || 0)
    const ltBorr = Number(bal.lt_borr || 0)
    const bond = Number(bal.bond_payable || 0)
    const interestDebt = stBorr + ltBorr + bond

    const finExp = incCur ? Number(incCur.fin_exp || 0) : 0

    let detail = `货币资金: ${formatNumber(cash / 1e8, 2)}亿, 有息负债: ${formatNumber(interestDebt / 1e8, 2)}亿`

    if (cash > interestDebt && interestDebt > 0) {
      const impliedRate = interestDebt ? Math.abs(finExp) / interestDebt * 100 : 0
      detail += `, 隐含利率: ${formatNumber(impliedRate, 2)}%`

      if (impliedRate > 4) {
        return this.fail(detail + ' → 大存大贷且高息', { cash, interest_debt: interestDebt })
      } else if (impliedRate > 2) {
        return this.warn(detail, { cash, interest_debt: interestDebt })
      }
      return this.pass(detail, { cash, interest_debt: interestDebt })
    }
    return this.pass(detail + ' → 货币资金 < 有息负债', { cash, interest_debt: interestDebt })
  }
}

// ==================== Layer 3: 资产负债表信号 ====================

class Rule3_1 extends BaseRule {
  code = '3.1'
  name = '应收增速异常'
  layer = 3
  weight_warn = 2
  weight_fail = 5

  evaluate(ctx: RuleContext): RuleResult {
    const balCur = latest(ctx.balance_list)
    const balPrev = prev(ctx.balance_list)
    const incCur = latest(ctx.income_list)
    const incPrev = prev(ctx.income_list)

    if (!balCur || !balPrev || !incCur || !incPrev) {
      return this.skip('数据不足')
    }

    const arCur = Number(balCur.accounts_receiv || 0)
    const arPrev = Number(balPrev.accounts_receiv || 0)
    const revCur = Number(incCur.revenue || 0)
    const revPrev = Number(incPrev.revenue || 0)

    if (arPrev === 0 || revPrev === 0) {
      return this.skip('基期为0')
    }

    const arGrowth = (arCur - arPrev) / arPrev * 100
    const revGrowth = (revCur - revPrev) / revPrev * 100
    const ratio = revGrowth ? arGrowth / revGrowth : 0

    const detail = `应收增速: ${formatNumber(arGrowth, 1)}%, 营收增速: ${formatNumber(revGrowth, 1)}%, 比率: ${formatNumber(ratio, 2)}`

    if (revGrowth > 0 && ratio > 2) {
      return this.fail(detail + ' → 应收增速远超营收', { ar_growth: arGrowth, rev_growth: revGrowth, ratio })
    } else if (revGrowth <= 0 || ratio > 1.5) {
      return this.warn(detail, { ar_growth: arGrowth, rev_growth: revGrowth, ratio })
    }
    return this.pass(detail, { ar_growth: arGrowth, rev_growth: revGrowth, ratio })
  }
}

class Rule3_2 extends BaseRule {
  code = '3.2'
  name = '存货与毛利率背离'
  layer = 3
  weight_warn = 2
  weight_fail = 5

  evaluate(ctx: RuleContext): RuleResult {
    const indCur = latest(ctx.indicator_list)
    const indPrev = prev(ctx.indicator_list)

    if (!indCur || !indPrev) {
      return this.skip('无指标数据')
    }

    const invTurnCur = Number(indCur.inv_turn || 0)
    const invTurnPrev = Number(indPrev.inv_turn || 0)
    const gmCur = Number(indCur.grossprofit_margin || 0)
    const gmPrev = Number(indPrev.grossprofit_margin || 0)

    if (invTurnPrev === 0) {
      return this.skip('基期周转率为0')
    }

    const invTurnChange = (invTurnCur - invTurnPrev) / invTurnPrev * 100
    const gmChange = gmCur - gmPrev

    const detail = `存货周转率变化: ${formatNumber(invTurnChange, 1)}%, 毛利率变化: ${formatNumber(gmChange, 2)}pp`
    const isCombo = invTurnChange < -20 && gmChange > 3

    if (isCombo) {
      return this.fail(detail + ' → 黄金造假组合', { inv_turn_change: invTurnChange, gm_change: gmChange, is_combo: isCombo })
    } else if (invTurnChange < -10 && gmChange > 0) {
      return this.warn(detail, { inv_turn_change: invTurnChange, gm_change: gmChange, is_combo: isCombo })
    }
    return this.pass(detail, { inv_turn_change: invTurnChange, gm_change: gmChange, is_combo: isCombo })
  }
}

class Rule3_3 extends BaseRule {
  code = '3.3'
  name = '在建工程异常'
  layer = 3
  weight_warn = 2
  weight_fail = 5

  evaluate(ctx: RuleContext): RuleResult {
    if (ctx.balance_list.length < 3) {
      return this.skip('数据不足3年')
    }

    let years = 0
    const len = Math.min(5, ctx.balance_list.length)
    for (let i = 0; i < len; i++) {
      if (i + 1 >= ctx.balance_list.length) break
      const balCur = ctx.balance_list[i]
      const balPrev = ctx.balance_list[i + 1]

      const cipCur = Number(balCur.cip || 0)
      const cipPrev = Number(balPrev.cip || 0)
      const fixCur = Number(balCur.fix_assets || 0)
      const fixPrev = Number(balPrev.fix_assets || 0)

      if (cipPrev > 0) {
        const cipGrowth = (cipCur - cipPrev) / cipPrev * 100
        const fixGrowth = fixPrev ? (fixCur - fixPrev) / fixPrev * 100 : 0
        if (cipGrowth > 30 && fixGrowth < cipGrowth * 0.5) {
          years++
        }
      }
    }

    const detail = `在建工程持续异常增长: ${years}年`

    if (years >= 3) {
      return this.fail(detail, { years })
    } else if (years >= 1) {
      return this.warn(detail, { years })
    }
    return this.pass(detail, { years })
  }
}

class Rule3_4 extends BaseRule {
  code = '3.4'
  name = '长期待摊费用异常'
  layer = 3
  weight_warn = 2
  weight_fail = 5

  evaluate(ctx: RuleContext): RuleResult {
    const balCur = latest(ctx.balance_list)
    const balPrev = prev(ctx.balance_list)

    if (!balCur) {
      return this.skip('无资产负债表数据')
    }

    const ltAmort = Number(balCur.lt_amort_deferred_exp || 0)
    const totalAssets = Number(balCur.total_assets || 1)
    const ratio = totalAssets ? ltAmort / totalAssets * 100 : 0

    let yoyChange = 0
    if (balPrev) {
      const ltAmortPrev = Number(balPrev.lt_amort_deferred_exp || 0)
      if (ltAmortPrev > 0) {
        yoyChange = (ltAmort - ltAmortPrev) / ltAmortPrev * 100
      }
    }

    const detail = `长期待摊: ${formatNumber(ltAmort / 1e8, 2)}亿, 占资产: ${formatNumber(ratio, 2)}%, YoY: ${formatNumber(yoyChange, 1)}%`

    if (yoyChange > 100 || ratio > 1) {
      return this.fail(detail, { lt_amort: ltAmort, ratio, yoy_change: yoyChange })
    } else if (yoyChange > 50) {
      return this.warn(detail, { lt_amort: ltAmort, ratio, yoy_change: yoyChange })
    }
    return this.pass(detail, { lt_amort: ltAmort, ratio, yoy_change: yoyChange })
  }
}

class Rule3_5 extends BaseRule {
  code = '3.5'
  name = '坏账计提不足'
  layer = 3
  weight_warn = 2
  weight_fail = 5

  evaluate(ctx: RuleContext): RuleResult {
    const incCur = latest(ctx.income_list)
    const balCur = latest(ctx.balance_list)

    if (!incCur || !balCur) {
      return this.skip('数据不足')
    }

    const creditLoss = Math.abs(Number(incCur.credit_impa_loss || 0))
    const ar = Number(balCur.accounts_receiv || 0)

    if (ar === 0) {
      return this.pass('应收账款为0')
    }

    const badDebtRatio = ar ? creditLoss / ar * 100 : 0
    const peerRatio = Number(ctx.peer_indicators.bad_debt_ratio_median || 0)

    let detail = `坏账计提比例: ${formatNumber(badDebtRatio, 2)}%`

    if (peerRatio) {
      detail += `, 同行中位数: ${formatNumber(peerRatio, 2)}%`
      if (peerRatio > 0 && badDebtRatio < peerRatio * 0.5) {
        return this.fail(detail + ' → 远低于同行', { bad_debt_ratio: badDebtRatio, peer_ratio: peerRatio })
      } else if (badDebtRatio < peerRatio) {
        return this.warn(detail + ' → 低于同行', { bad_debt_ratio: badDebtRatio, peer_ratio: peerRatio })
      }
      return this.pass(detail, { bad_debt_ratio: badDebtRatio, peer_ratio: peerRatio })
    } else {
      const histRatios: number[] = []
      const maxHist = Math.min(4, ctx.income_list.length)
      for (let i = 1; i < maxHist; i++) {
        if (i < ctx.income_list.length && i < ctx.balance_list.length) {
          const inc = ctx.income_list[i]
          const bal = ctx.balance_list[i]
          const cl = Math.abs(Number(inc.credit_impa_loss || 0))
          const arHist = Number(bal.accounts_receiv || 0)
          if (arHist > 0) {
            histRatios.push(cl / arHist * 100)
          }
        }
      }

      if (histRatios.length > 0) {
        const avgHist = histRatios.reduce((a, b) => a + b, 0) / histRatios.length
        detail += `, 历史均值: ${formatNumber(avgHist, 2)}%`
        if (avgHist > 0 && badDebtRatio < avgHist * 0.5) {
          return this.fail(detail + ' → 远低于历史均值', { bad_debt_ratio: badDebtRatio, peer_ratio: peerRatio })
        } else if (badDebtRatio < avgHist * 0.7) {
          return this.warn(detail + ' → 低于历史均值', { bad_debt_ratio: badDebtRatio, peer_ratio: peerRatio })
        }
        return this.pass(detail, { bad_debt_ratio: badDebtRatio, peer_ratio: peerRatio })
      }
      return this.pass(detail + ' → 无对比基准', { bad_debt_ratio: badDebtRatio, peer_ratio: peerRatio })
    }
  }
}

// ==================== Layer 4: 交叉验证 ====================

class Rule4_1 extends BaseRule {
  code = '4.1'
  name = '净现比异常'
  layer = 4
  weight_warn = 3
  weight_fail = 7

  evaluate(ctx: RuleContext): RuleResult {
    if (ctx.cashflow_list.length < 3) {
      return this.skip('数据不足3年')
    }

    let yearsBelow1 = 0
    const len = Math.min(5, ctx.cashflow_list.length)
    for (let i = 0; i < len; i++) {
      if (i >= ctx.income_list.length) break
      const cf = ctx.cashflow_list[i]
      const inc = ctx.income_list[i]

      const operCf = Number(cf.n_cashflow_act || 0)
      const netProfit = Number(inc.n_income_attr_p || 0)

      if (netProfit > 0 && operCf > 0 && operCf / netProfit < 1) {
        yearsBelow1++
      }
    }

    const detail = `近5年净现比<1: ${yearsBelow1}年`

    if (yearsBelow1 >= 3) {
      return this.fail(detail, { years_below_1: yearsBelow1 })
    } else if (yearsBelow1 >= 2) {
      return this.warn(detail, { years_below_1: yearsBelow1 })
    }
    return this.pass(detail, { years_below_1: yearsBelow1 })
  }
}

class Rule4_2 extends BaseRule {
  code = '4.2'
  name = '收现比异常'
  layer = 4
  weight_warn = 3
  weight_fail = 7

  evaluate(ctx: RuleContext): RuleResult {
    if (ctx.cashflow_list.length < 2) {
      return this.skip('数据不足')
    }

    let yearsBelow = 0
    const len = Math.min(5, ctx.cashflow_list.length)
    for (let i = 0; i < len; i++) {
      if (i >= ctx.income_list.length) break
      const cf = ctx.cashflow_list[i]
      const inc = ctx.income_list[i]

      const cashRecp = Number(cf.c_recp_prov_sg_act || 0)
      const revenue = Number(inc.revenue || 0)

      if (revenue > 0 && cashRecp / revenue < 0.8) {
        yearsBelow++
      }
    }

    const detail = `近5年收现比<0.8: ${yearsBelow}年`

    if (yearsBelow >= 2) {
      return this.fail(detail, { years_below: yearsBelow })
    } else if (yearsBelow >= 1) {
      return this.warn(detail, { years_below: yearsBelow })
    }
    return this.pass(detail, { years_below: yearsBelow })
  }
}

class Rule4_3 extends BaseRule {
  code = '4.3'
  name = '资产利润背离'
  layer = 4
  weight_warn = 3
  weight_fail = 7

  evaluate(ctx: RuleContext): RuleResult {
    if (ctx.balance_list.length < 2) {
      return this.skip('数据不足')
    }

    let yearsAbnormal = 0
    const len = Math.min(5, ctx.balance_list.length - 1)
    for (let i = 0; i < len; i++) {
      if (i + 1 >= ctx.balance_list.length || i >= ctx.income_list.length) break

      const balCur = ctx.balance_list[i]
      const balPrev = ctx.balance_list[i + 1]
      const inc = ctx.income_list[i]

      const totalAssetsCur = Number(balCur.total_assets || 0)
      const totalAssetsPrev = Number(balPrev.total_assets || 0)
      const netProfit = Number(inc.n_income_attr_p || 0)

      if (totalAssetsPrev > 0 && netProfit > 0) {
        const assetGrowth = (totalAssetsCur - totalAssetsPrev) / totalAssetsPrev * 100
        if (assetGrowth > 30) {
          yearsAbnormal++
        }
      }
    }

    const detail = `资产膨胀异常: ${yearsAbnormal}年`

    if (yearsAbnormal >= 2) {
      return this.fail(detail, { years_abnormal: yearsAbnormal })
    } else if (yearsAbnormal >= 1) {
      return this.warn(detail, { years_abnormal: yearsAbnormal })
    }
    return this.pass(detail, { years_abnormal: yearsAbnormal })
  }
}

class Rule4_4 extends BaseRule {
  code = '4.4'
  name = '核心利润背离'
  layer = 4
  weight_warn = 3
  weight_fail = 7

  evaluate(ctx: RuleContext): RuleResult {
    const incCur = latest(ctx.income_list)

    if (!incCur) {
      return this.skip('无利润表数据')
    }

    const revenue = Number(incCur.revenue || 0)
    const operCost = Number(incCur.oper_cost || 0)
    const sellExp = Number(incCur.sell_exp || 0)
    const adminExp = Number(incCur.admin_exp || 0)
    const finExp = Number(incCur.fin_exp || 0)
    const netProfit = Number(incCur.n_income_attr_p || 0)

    const coreProfit = revenue - operCost - sellExp - adminExp - finExp

    if (netProfit === 0) {
      return this.skip('净利润为0')
    }

    const divergence = Math.abs(coreProfit - netProfit) / Math.abs(netProfit) * 100

    const detail = `核心利润: ${formatNumber(coreProfit / 1e8, 2)}亿, 净利润: ${formatNumber(netProfit / 1e8, 2)}亿, 背离度: ${formatNumber(divergence, 1)}%`

    if (divergence > 40) {
      return this.fail(detail, { core_profit: coreProfit, net_profit: netProfit, divergence })
    } else if (divergence > 20) {
      return this.warn(detail, { core_profit: coreProfit, net_profit: netProfit, divergence })
    }
    return this.pass(detail, { core_profit: coreProfit, net_profit: netProfit, divergence })
  }
}

class Rule4_5 extends BaseRule {
  code = '4.5'
  name = '盈利与自由现金背离'
  layer = 4
  weight_warn = 3
  weight_fail = 7

  evaluate(ctx: RuleContext): RuleResult {
    if (ctx.indicator_list.length < 3) {
      return this.skip('数据不足3年')
    }

    let yearsAbnormal = 0
    const len = Math.min(5, ctx.indicator_list.length)
    for (let i = 0; i < len; i++) {
      if (i >= ctx.income_list.length) break
      const inc = ctx.income_list[i]

      const netProfit = Number(inc.n_income_attr_p || 0)
      const netProfitPrev = i + 1 < ctx.income_list.length
        ? Number(ctx.income_list[i + 1].n_income_attr_p || 0)
        : 0

      let fcff = 0
      if (i < ctx.cashflow_list.length) {
        fcff = Number(ctx.cashflow_list[i].free_cashflow || 0)
      }

      if (netProfit > 0 && netProfit > netProfitPrev && fcff < 0) {
        yearsAbnormal++
      }
    }

    const detail = `盈利增长但FCF为负: ${yearsAbnormal}年`

    if (yearsAbnormal >= 3) {
      return this.fail(detail, { years_abnormal: yearsAbnormal })
    } else if (yearsAbnormal >= 2) {
      return this.warn(detail, { years_abnormal: yearsAbnormal })
    }
    return this.pass(detail, { years_abnormal: yearsAbnormal })
  }
}

// ==================== Layer 5: 非财务信号 ====================

class Rule5_1 extends BaseRule {
  code = '5.1'
  name = '更换审计机构'
  layer = 5
  weight_warn = 1
  weight_fail = 3

  evaluate(ctx: RuleContext): RuleResult {
    if (ctx.income_list.length < 3) {
      return this.skip('数据不足3年')
    }
    const agency = ctx.audit_agency || ''
    const detail = `当前审计机构: ${agency || '无数据'} → PASS (需多年数据对比)`
    return this.pass(detail)
  }
}

class Rule5_2 extends BaseRule {
  code = '5.2'
  name = '大股东减持'
  layer = 5
  weight_warn = 1
  weight_fail = 3

  evaluate(ctx: RuleContext): RuleResult {
    return this.pass('大股东减持 → PASS (需股东数据)')
  }
}

class Rule5_3 extends BaseRule {
  code = '5.3'
  name = '高管变更'
  layer = 5
  weight_warn = 1
  weight_fail = 3

  evaluate(ctx: RuleContext): RuleResult {
    return this.pass('财务总监变更 → PASS (需PDF数据)')
  }
}

class Rule5_4 extends BaseRule {
  code = '5.4'
  name = '独董辞职'
  layer = 5
  weight_warn = 1
  weight_fail = 3

  evaluate(ctx: RuleContext): RuleResult {
    return this.pass('独立董事辞职 → PASS (需PDF数据)')
  }
}

class Rule5_5 extends BaseRule {
  code = '5.5'
  name = '客户集中度'
  layer = 5
  weight_warn = 1
  weight_fail = 3

  evaluate(ctx: RuleContext): RuleResult {
    return this.pass('客户集中度 → PASS (需PDF数据)')
  }
}

class Rule5_6 extends BaseRule {
  code = '5.6'
  name = '频繁并购'
  layer = 5
  weight_warn = 1
  weight_fail = 3

  evaluate(ctx: RuleContext): RuleResult {
    return this.pass('跨行业收购 → PASS (需PDF数据)')
  }
}

// ==================== Layer 6: 行业特有风险 ====================

class Rule6_1 extends BaseRule {
  code = '6.1'
  name = '行业风险'
  layer = 6
  weight_warn = 1
  weight_fail = 3

  private RISKY_INDUSTRIES = ['农业', '林业', '渔业', '牧业', '畜牧', '养殖', '种植', '饲料', '水产']

  evaluate(ctx: RuleContext): RuleResult {
    const industry = ctx.industry || ''
    const detail = `行业: ${industry || '无数据'}`
    const isRisky = this.RISKY_INDUSTRIES.some(r => industry.includes(r))

    if (isRisky) {
      return this.warn(detail + ' → 生物资产难以审计')
    }
    return this.pass(detail)
  }
}

class Rule6_2 extends BaseRule {
  code = '6.2'
  name = '研发资本化'
  layer = 6
  weight_warn = 1
  weight_fail = 3

  evaluate(ctx: RuleContext): RuleResult {
    const capRatio = ctx.pdf_data.rd_cap_ratio

    if (capRatio === undefined || capRatio === null) {
      return this.skip('PDF中未找到研发资本化数据')
    }

    const detail = `研发资本化比例: ${formatNumber(capRatio, 1)}%`

    if (Number(capRatio) > 50) {
      return this.fail(detail)
    } else if (Number(capRatio) > 30) {
      return this.warn(detail)
    }
    return this.pass(detail)
  }
}

// ==================== 规则引擎 ====================

export class RuleEngine {
  private rules: BaseRule[]

  constructor() {
    this.rules = [
      new Rule0_1(), new Rule0_2(),
      new Rule1_1(), new Rule1_2(), new Rule1_3(), new Rule1_4(), new Rule1_5(), new Rule1_6(),
      new Rule2_1(), new Rule2_2(), new Rule2_3(),
      new Rule3_1(), new Rule3_2(), new Rule3_3(), new Rule3_4(), new Rule3_5(),
      new Rule4_1(), new Rule4_2(), new Rule4_3(), new Rule4_4(), new Rule4_5(),
      new Rule5_1(), new Rule5_2(), new Rule5_3(), new Rule5_4(), new Rule5_5(), new Rule5_6(),
      new Rule6_1(), new Rule6_2(),
    ]
  }

  analyze(ctx: RuleContext, reportYear: number = 2024): ReportResult {
    const result: ReportResult = {
      stock_code: ctx.stock_code,
      stock_name: ctx.stock_name,
      report_year: reportYear,
      total_score: 0,
      risk_level: RiskLevel.LOW,
      rule_results: [],
      combo_bonus: 0,
      n_pass: 0,
      n_warn: 0,
      n_fail: 0,
      n_skip: 0,
    }

    for (const rule of this.rules) {
      const ruleResult = rule.evaluate(ctx)
      result.rule_results.push(ruleResult)

      if (rule.layer === 0 && ruleResult.verdict === Verdict.FAIL) {
        result.n_fail++
        result.total_score = 999
        result.risk_level = RiskLevel.REJECT
        result.rule_results[result.rule_results.length - 1].score_added = 999
        return result
      }

      if (ruleResult.verdict === Verdict.PASS) {
        result.n_pass++
      } else if (ruleResult.verdict === Verdict.WARN) {
        result.n_warn++
        result.total_score += ruleResult.score_added
      } else if (ruleResult.verdict === Verdict.FAIL) {
        result.n_fail++
        result.total_score += ruleResult.score_added
      } else if (ruleResult.verdict === Verdict.SKIP) {
        result.n_skip++
      }
    }

    result.combo_bonus = this.calcComboBonus(result.rule_results)
    result.total_score += result.combo_bonus
    result.risk_level = this.calcRiskLevel(result.total_score)

    return result
  }

  private calcComboBonus(ruleResults: RuleResult[]): number {
    let bonus = 0

    const r32 = ruleResults.find(r => r.code === '3.2')
    if (r32 && r32.verdict === Verdict.FAIL) {
      bonus += 10
    }

    const r23 = ruleResults.find(r => r.code === '2.3')
    const r41 = ruleResults.find(r => r.code === '4.1')
    if (r23 && r23.verdict === Verdict.FAIL && r41 && r41.verdict === Verdict.FAIL) {
      bonus += 8
    }

    const r12 = ruleResults.find(r => r.code === '1.2')
    const r31 = ruleResults.find(r => r.code === '3.1')
    if (r12 && r12.verdict === Verdict.FAIL && r31 && r31.verdict === Verdict.FAIL) {
      bonus += 6
    }

    return bonus
  }

  private calcRiskLevel(score: number): RiskLevel {
    if (score >= 46) return RiskLevel.VERY_HIGH
    if (score >= 26) return RiskLevel.HIGH
    if (score >= 11) return RiskLevel.MEDIUM
    return RiskLevel.LOW
  }
}

export const ruleEngine = new RuleEngine()
