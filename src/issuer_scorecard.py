"""
Issuer BIN Scorecard — GMV Recovery Priority
Straive Strategic Analytics
"""
import pandas as pd
import numpy as np
import logging

log = logging.getLogger(__name__)

THRESHOLDS = {"auth_rate": 0.90, "dnh_rate": 0.025, "technical_rate": 0.008}

TIER_RULES = [
    ("Critical",        lambda r: r["auth_rate"] < 0.85),
    ("Needs Attention", lambda r: r["auth_rate"] < 0.90),
    ("Good",            lambda r: r["auth_rate"] < 0.95),
    ("Excellent",       lambda r: True),
]

def score_bins(df: pd.DataFrame) -> pd.DataFrame:
    """Score each BIN prefix and assign performance tier."""
    bin_stats = df.groupby("bin_prefix").agg(
        total_attempts=("txn_id","count"),
        approvals=("is_approved","sum"),
        dnh_count=("is_dnh","sum"),
        technical_count=("is_technical","sum"),
        total_gmv=("amount","sum"),
        declined_gmv=("declined_amount","sum"),
        issuer_name=("issuer_name","first"),
    ).reset_index()

    bin_stats["auth_rate"]      = bin_stats["approvals"] / bin_stats["total_attempts"]
    bin_stats["dnh_rate"]       = bin_stats["dnh_count"] / bin_stats["total_attempts"]
    bin_stats["technical_rate"] = bin_stats["technical_count"] / bin_stats["total_attempts"]
    bin_stats["vs_threshold"]   = bin_stats["auth_rate"] - THRESHOLDS["auth_rate"]
    bin_stats["gmv_at_risk"]    = (THRESHOLDS["auth_rate"] - bin_stats["auth_rate"]).clip(0) * bin_stats["total_gmv"]

    def assign_tier(row):
        for name, rule in TIER_RULES:
            if rule(row): return name
        return "Excellent"

    bin_stats["performance_tier"] = bin_stats.apply(assign_tier, axis=1)
    log.info("BIN tier distribution:\n" + bin_stats["performance_tier"].value_counts().to_string())
    return bin_stats.sort_values("gmv_at_risk", ascending=False)
