"""
finscan 批次0 - Baostock 数据源可行性验证脚本
目标：
1. 验证 Baostock 登录与数据接口可用性
2. 探明 balance / profit / cashflow / growth / operation /Dupont 等接口的真实字段清单
3. 采集茅台(600519.SH)近6年年报，导出真实数据样本
4. 输出每个接口的字段完整 JSON，供 field_mapping.md 归纳

输出：
- docs/probe_baostock_fields.json   各接口字段清单
- docs/probe_baostock_sample.csv    茅台近6年数据样本
"""
import sys
import os
import json
import datetime as dt

import baostock as bs
import pandas as pd

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
SAMPLE_CODE = "sh.600519"  # 茅台 (Baostock 用小写 sh./sz.)
START_YEAR = dt.date.today().year - 6  # 近6年
START_DATE = f"{START_YEAR}-01-01"
END_DATE = f"{dt.date.today().year}-12-31"

# 待探测的 Baostock 接口及其调用参数
PROBES = [
    # (接口中文名, 调用函数名, kwargs)
    ("资产负债表", "query_balance_data", {}),
    ("利润表", "query_profit_data", {}),
    ("现金流量表", "query_cash_flow_data", {}),
    ("成长能力指标", "query_growth_data", {}),
    ("营运能力指标", "query_operation_data", {}),
    ("盈利能力指标", "query_profit_data_dupont", {}),  # 杜邦分析
    ("偿债能力指标", "query_balance_data_extra", {}),  # 可能不存在
]


def login():
    lg = bs.login()
    print(f"[login] code={lg.error_code} msg={lg.error_msg}")
    if lg.error_code != "0":
        sys.exit("Baostock 登录失败，终止探测")


def safe_call(func_name, **kwargs):
    """安全调用，返回 (rs, 字段列表, 是否成功)"""
    func = getattr(bs, func_name, None)
    if func is None:
        return None, [], False, f"接口 {func_name} 不存在"
    try:
        rs = func(**kwargs)
        if rs.error_code != "0":
            return rs, [], False, f"{rs.error_code}: {rs.error_msg}"
        fields = rs.fields.split(",") if rs.fields else []
        return rs, fields, True, "ok"
    except Exception as e:
        return None, [], False, repr(e)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    login()

    # ===== 1. 先探测基础信息接口（股票列表）=====
    print("\n===== 1) 全A股基础信息 =====")
    rs = bs.query_stock_basic()
    basic_fields = rs.fields.split(",") if rs.error_code == "0" else []
    print(f"  query_stock_basic 字段({len(basic_fields)}): {basic_fields}")
    # 取茅台基础信息
    rs_mty = bs.query_stock_basic(code=SAMPLE_CODE)
    mty_basic = {}
    while rs_mty.next():
        mty_basic = rs_mty.get_row_data()
    print(f"  茅台基础信息: {mty_basic}")

    # ===== 2. 探测各财务接口的字段清单（用茅台1期）=====
    print("\n===== 2) 各财务接口字段探测 =====")
    probe_fields = {"_meta": {"sample_code": SAMPLE_CODE, "basic_fields": basic_fields, "mty_basic": mty_basic}}

    iface_kwargs_sets = {
        "query_balance_data": dict(code=SAMPLE_CODE, year=dt.date.today().year - 1, quarter=4),
        "query_profit_data": dict(code=SAMPLE_CODE, year=dt.date.today().year - 1, quarter=4),
        "query_cash_flow_data": dict(code=SAMPLE_CODE, year=dt.date.today().year - 1, quarter=4),
        "query_growth_data": dict(code=SAMPLE_CODE, year=dt.date.today().year - 1, quarter=4),
        "query_operation_data": dict(code=SAMPLE_CODE, year=dt.date.today().year - 1, quarter=4),
        "query_dupont_data": dict(code=SAMPLE_CODE, year=dt.date.today().year - 1, quarter=4),
        "query_operation_data_extra": dict(code=SAMPLE_CODE, year=dt.date.today().year - 1, quarter=4),
    }

    for func_name, kwargs in iface_kwargs_sets.items():
        rs, fields, ok, msg = safe_call(func_name, **kwargs)
        sample_row = []
        if ok and rs is not None:
            while rs.next():
                sample_row = rs.get_row_data()
                break
        probe_fields[func_name] = {
            "fields": fields,
            "field_count": len(fields),
            "sample_row": sample_row,
            "ok": ok,
            "msg": msg,
        }
        status = "OK" if ok else "MISSING/FAIL"
        print(f"  [{status}] {func_name}: {len(fields)}字段  ({msg})")

    # ===== 3. 探测 query_history_k / 业绩快报 / 预告（如有）=====
    print("\n===== 3) 业绩预告/快报 =====")
    for func_name in ["query_performance_express_report", "query_forcast_report"]:
        rs, fields, ok, msg = safe_call(func_name, code=SAMPLE_CODE,
                                        start_date=START_DATE, end_date=END_DATE)
        sample_row = []
        if ok and rs is not None:
            while rs.next():
                sample_row = rs.get_row_data()
                break
        probe_fields[func_name] = {"fields": fields, "ok": ok, "msg": msg, "sample_row": sample_row}
        print(f"  [{'OK' if ok else 'FAIL'}] {func_name}: {msg}")

    # ===== 4. 采集茅台近6年年报（profit/balance/cashflow）合并样本 =====
    print("\n===== 4) 采集茅台近6年年报合并样本 =====")
    years = list(range(START_YEAR, dt.date.today().year))
    sample_rows = []
    for y in years:
        for stmt, fn in [("balance", "query_balance_data"), ("profit", "query_profit_data"), ("cashflow", "query_cash_flow_data")]:
            rs, _, ok, msg = safe_call(fn, code=SAMPLE_CODE, year=y, quarter=4)
            if ok and rs is not None:
                while rs.next():
                    row = rs.get_row_data()
                    sample_rows.append({"year": y, "statement": stmt, **dict(zip(rs.fields.split(","), row))})
    df = pd.DataFrame(sample_rows)
    sample_path = os.path.join(OUT_DIR, "probe_baostock_sample.csv")
    df.to_csv(sample_path, index=False)
    print(f"  采集 {len(sample_rows)} 行，已写入 {sample_path}")

    fields_path = os.path.join(OUT_DIR, "probe_baostock_fields.json")
    with open(fields_path, "w", encoding="utf-8") as f:
        json.dump(probe_fields, f, ensure_ascii=False, indent=2)
    print(f"  字段清单已写入 {fields_path}")

    bs.logout()
    print("\n✅ Baostock 探测完成")


if __name__ == "__main__":
    main()
