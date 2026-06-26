"""财报排雷引擎"""
from .rules import (
    RuleEngine,
    RuleContext,
    RuleResult,
    ReportResult,
    Verdict,
    RiskLevel,
    BaseRule,
    # Layer 0
    Rule0_1, Rule0_2,
    # Layer 1
    Rule1_1, Rule1_2, Rule1_3, Rule1_4, Rule1_5, Rule1_6,
    # Layer 2
    Rule2_1, Rule2_2, Rule2_3,
    # Layer 3
    Rule3_1, Rule3_2, Rule3_3, Rule3_4, Rule3_5,
    # Layer 4
    Rule4_1, Rule4_2, Rule4_3, Rule4_4, Rule4_5,
    # Layer 5
    Rule5_1, Rule5_2, Rule5_3, Rule5_4, Rule5_5, Rule5_6,
    # Layer 6
    Rule6_1, Rule6_2,
)

__all__ = [
    "RuleEngine",
    "RuleContext",
    "RuleResult",
    "ReportResult",
    "Verdict",
    "RiskLevel",
    "BaseRule",
    "Rule0_1", "Rule0_2",
    "Rule1_1", "Rule1_2", "Rule1_3", "Rule1_4", "Rule1_5", "Rule1_6",
    "Rule2_1", "Rule2_2", "Rule2_3",
    "Rule3_1", "Rule3_2", "Rule3_3", "Rule3_4", "Rule3_5",
    "Rule4_1", "Rule4_2", "Rule4_3", "Rule4_4", "Rule4_5",
    "Rule5_1", "Rule5_2", "Rule5_3", "Rule5_4", "Rule5_5", "Rule5_6",
    "Rule6_1", "Rule6_2",
]
