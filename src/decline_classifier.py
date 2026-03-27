"""
Decline Root-Cause Classifier — Acquirer Authorization Analytics
Straive Strategic Analytics
"""
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
import logging

log = logging.getLogger(__name__)

# ISO 8583 response code taxonomy
DECLINE_TAXONOMY = {
    "51":"INSUFFICIENT_FUNDS","61":"INSUFFICIENT_FUNDS","65":"INSUFFICIENT_FUNDS",
    "05":"FALSE_DECLINE","57":"FALSE_DECLINE","62":"FALSE_DECLINE","93":"FALSE_DECLINE","14":"FALSE_DECLINE",
    "55":"VELOCITY_CONTROL","75":"VELOCITY_CONTROL","06":"VELOCITY_CONTROL",
    "91":"TECHNICAL","92":"TECHNICAL","96":"TECHNICAL",
    "41":"CARD_RESTRICTION","43":"CARD_RESTRICTION","54":"CARD_RESTRICTION",
    "12":"OTHER","13":"OTHER","15":"OTHER",
}
ACTIONABLE = {"FALSE_DECLINE","TECHNICAL","VELOCITY_CONTROL"}

def classify(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["decline_category"] = df["response_code"].map(DECLINE_TAXONOMY).fillna("OTHER")
    df["is_actionable"]    = df["decline_category"].isin(ACTIONABLE)
    df["is_false_decline"] = df["decline_category"] == "FALSE_DECLINE"
    return df

def waterfall(df: pd.DataFrame) -> pd.DataFrame:
    declined = classify(df[df["is_declined"] == 1])
    wf = declined.groupby("decline_category").agg(
        txn_count=("txn_id","count"), gmv=("amount","sum")
    ).assign(
        pct_volume=lambda x: x["txn_count"]/x["txn_count"].sum()*100,
        actionable=lambda x: x.index.isin(ACTIONABLE),
    ).sort_values("txn_count", ascending=False)
    log.info("Decline waterfall:\n" + wf.to_string())
    return wf

def train_ml_classifier(df: pd.DataFrame):
    """Augment rule-based taxonomy with ML for ambiguous codes."""
    features = ["amount","merchant_type_encoded","hour_of_day","is_cnp","is_cross_border"]
    X = df[features].fillna(0)
    y = df["decline_category"]
    clf = DecisionTreeClassifier(max_depth=6, min_samples_leaf=200, random_state=42)
    clf.fit(X, y)
    log.info(f"ML classifier trained | classes: {clf.classes_}")
    return clf
