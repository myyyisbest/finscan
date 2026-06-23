"""finscan 数据初始化采集脚本。

用法:
    # 抓取 sample list（默认3只，用于快速验证链路
    python -m scripts.init_collect

    # 采集全部 A 股
    COLLECT_SCOPE=all python -m scripts.init_collect
"""
import sys
from pathlib import Path

# 允许从 backend/ 执行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.logger import setup_logging, get_logger  # noqa: E402
from app.collector.sina_adapter import collect_one_stock  # noqa: E402
from app.collector.em_indicator import collect_indicators  # noqa: E402


# ---- 样例与全量清单 ----
# 目标采集股票（航天电子、信维通信、西部材料）
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
    """尝试通过 akshare 获取全量 A 股代码。若失败则使用 sample。"""
    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        rows = []
        for _, row in df.iterrows():
            code = row["code"]
            name = row["name"]
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

    ok = 0
    failed = 0
    for idx, (stock_code, stock_name) in enumerate(stocks, 1):
        log.info("(%d/%d) 采集 %s %s", idx, len(stocks), stock_code, stock_name)
        try:
            stats = collect_one_stock(stock_code, stock_name)
            log.info("  -> 三表结果: %s", stats)
            # 指标自算
            n = collect_indicators(stock_code)
            log.info("  -> 指标写入: %d", n)
            ok += 1
        except Exception as exc:  # noqa: BLE001
            log.exception("  -> 采集异常: %s", exc)
            failed += 1

    log.info("采集完成: ok=%d, failed=%d", ok, failed)


if __name__ == "__main__":
    main()
