"""finscan 数据采集适配器。

采集器按数据源拆分：
- sina_adapter: 新浪三表（资产负债表/利润表/现金流量表
- em_indicator: 同花顺(原东财)财务指标接口（ROE/ROA/周转率/偿债能力等
- em_zygc: 东财主营构成附注
- base: 适配器基类

主实现重试/随机延时/熔断保护
"""

from .base import BaseCollector
from .sina_adapter import SinaFinancialCollector
from .em_indicator import THSIndicatorCollector

__all__ = [
    "BaseCollector", "SinaFinancialCollector", "THSIndicatorCollector",
]
