"""finscan 数据初始化采集脚本（Sina + Tencent 数据源，避开被封的 EM datacenter）。

用法:
    # 抓取 sample list（默认3只，用于快速验证链路）
    python -m scripts.init_collect

    # 采集全部 A 股
    COLLECT_SCOPE=all python -m scripts.init_collect

    # 采集指定股票
    COLLECT_SCOPE=target python -m scripts.init_collect

数据采集顺序（依赖关系）:
    1. 腾讯行情/估值/股本 (quote)    —— 补齐 PE/PB/市值/股本/stock_name
    2. 三大报表 (sina_adapter)        —— Sina (新) 接口, 含行业
    3. 财务指标 (em_indicator)        —— THS 摘要 + 三表自算
    4. 公告 (em_announcement)         —— 当前网络下 EM 不可达, 暂跳过 (接口保留)

注意:
    EM datacenter (push2.eastmoney.com) 在本机网络被拒.
    替代方案: 腾讯 qt.gtimg.cn 提供 PE/PB/市值/股本 (替代 EM 行情);
              Sina quotes.sina.cn 提供三大报表 (替代 EM 财报).
"""
import sys
from pathlib import Path

# 允许从 backend/ 执行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.logger import setup_logging, get_logger  # noqa: E402
from app.collector.sina_adapter import collect_one_stock  # noqa: E402
from app.collector.em_indicator import collect_indicators  # noqa: E402
from app.collector.quote import collect_quote  # noqa: E402
from app.collector.sina_meta import collect_industry, collect_announcements  # noqa: E402


# ---- 样例与全量清单 ----
TARGET_LIST = [
    ("600879.SH", "航天电子"),
    ("300136.SZ", "信维通信"),
    ("002149.SZ", "西部材料"),
]

SAMPLE_LIST = [
    ("600519.SH", "贵州茅台"),
    ("000858.SZ", "五粮液"),
    ("000001.SZ", "平安银行"),
]


def _fetch_a_share_list():
    """通过 akshare 获取全量 A 股代码 (新浪接口, 稳定)."""
    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        rows = []
        for _, row in df.iterrows():
            code = str(row["code"])
            name = str(row["name"])
            if code.startswith(("6", "5", "68")):
                rows.append((f"{code}.SH", name))
            else:
                rows.append((f"{code}.SZ", name))
        return rows
    except Exception as exc:  # noqa: BLE001
        get_logger("init_collect").warning("拉取A股列表失败: %s", exc)
        return None


def main():
    setup_logging()
    log = get_logger("init_collect")

    scope = settings.COLLECT_SCOPE.lower() if hasattr(settings, "COLLECT_SCOPE") else "sample"
    if scope == "all":
        stocks = _fetch_a_share_list() or SAMPLE_LIST
        log.info("使用全量 A 股模式，共 %d 只", len(stocks))
    elif scope == "target":
        stocks = TARGET_LIST
        log.info("使用 target 模式，共 %d 只: %s", len(stocks), stocks)
    else:
        stocks = SAMPLE_LIST
        log.info("使用 sample 模式，共 %d 只: %s", len(stocks), stocks)

    # ---- 步骤 1: 腾讯行情/估值/股本 ----
    log.info("=== 步骤 1: 腾讯行情/估值 ===")
    try:
        results = collect_quote([c for c, _ in stocks])
        for r in results:
            log.info("  %s", r)
    except Exception as exc:  # noqa: BLE001
        log.exception("腾讯行情失败: %s", exc)

    # ---- 步骤 2: Sina 行业 (申万一级) ----
    log.info("=== 步骤 2: Sina 行业采集 ===")
    try:
        industry_map = collect_industry([c for c, _ in stocks])
        for k, v in industry_map.items():
            log.info("  %s -> %s", k, v)
    except Exception as exc:  # noqa: BLE001
        log.exception("Sina 行业失败: %s", exc)

    # ---- 步骤 3: 三大报表 (Sina) ----
    log.info("=== 步骤 3: 三大报表采集 ===")
    ok = 0
    failed = 0
    for idx, (stock_code, stock_name) in enumerate(stocks, 1):
        log.info("(%d/%d) 三大报表 %s %s", idx, len(stocks), stock_code, stock_name)
        try:
            stats = collect_one_stock(stock_code, stock_name)
            log.info("  -> 三表结果: %s", stats)
            ok += 1
        except Exception as exc:  # noqa: BLE001
            log.exception("  -> 三大报表异常: %s", exc)
            failed += 1

    # ---- 步骤 4: 财务指标 ----
    log.info("=== 步骤 4: 财务指标采集 ===")
    for idx, (stock_code, _) in enumerate(stocks, 1):
        try:
            n = collect_indicators(stock_code)
            log.info("  (%d/%d) [%s] 指标写入: %d", idx, len(stocks), stock_code, n)
        except Exception as exc:  # noqa: BLE001
            log.exception("  [%s] 指标异常: %s", stock_code, exc)

    # ---- 步骤 5: Sina 公告 (替代 EM 公告) ----
    log.info("=== 步骤 5: Sina 公告采集 ===")
    for idx, (stock_code, _) in enumerate(stocks, 1):
        try:
            n = collect_announcements(stock_code, pages=3)
            log.info("  (%d/%d) [%s] 公告解析: %d", idx, len(stocks), stock_code, len(n))
        except Exception as exc:  # noqa: BLE001
            log.exception("  [%s] 公告异常: %s", stock_code, exc)

    log.info("采集完成: ok=%d, failed=%d", ok, failed)


if __name__ == "__main__":
    main()
