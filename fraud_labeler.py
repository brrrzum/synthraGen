"""Post-processing fraud labeling engine for synthraGen outputs.

Implements deterministic rules for common fraud patterns and appends:
- is_fraud_rule: int (0/1)
- fraud_reasons: pipe-delimited reason codes

The module supports synthraGen's ISO-like field names and a normalized schema.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class LabelerConfig:
    tiny_amt_threshold: float = 5.0
    card_test_large_threshold: float = 500.0
    card_test_lookback_hours: int = 24
    velocity_window: str = "15min"
    velocity_txn_count_threshold: int = 4  # strictly greater than this
    impossible_travel_kmh: float = 900.0
    high_risk_mcc_threshold: float = 1000.0
    high_risk_mccs: tuple[str, ...] = ("5732", "6051", "5094")


def _coalesce_columns(df: pd.DataFrame, candidates: Iterable[str], target: str) -> None:
    for col in candidates:
        if col in df.columns:
            df[target] = df[col]
            return
    df[target] = pd.NA


def _normalize_input(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    _coalesce_columns(out, ["user_id", "Cust_ID", "customer_id"], "_user_id")
    _coalesce_columns(out, ["timestamp", "Timestamp"], "_timestamp")
    _coalesce_columns(out, ["amount", "DE004_Amount", "original_amount"], "_amount")
    _coalesce_columns(out, ["mcc", "MCC", "merchant_mcc"], "_mcc")
    _coalesce_columns(out, ["latitude", "lat"], "_lat")
    _coalesce_columns(out, ["longitude", "lon", "lng"], "_lon")

    out["_timestamp"] = pd.to_datetime(out["_timestamp"], errors="coerce", utc=True)
    out["_amount"] = pd.to_numeric(out["_amount"], errors="coerce")
    out["_mcc"] = out["_mcc"].astype("string")
    out["_lat"] = pd.to_numeric(out["_lat"], errors="coerce")
    out["_lon"] = pd.to_numeric(out["_lon"], errors="coerce")
    return out


def _haversine_km(lat1: pd.Series, lon1: pd.Series, lat2: pd.Series, lon2: pd.Series) -> pd.Series:
    r = 6371.0
    p1 = lat1.astype(float).map(math.radians)
    p2 = lat2.astype(float).map(math.radians)
    dphi = (lat2 - lat1).astype(float).map(math.radians)
    dlambda = (lon2 - lon1).astype(float).map(math.radians)

    a = (dphi / 2).map(math.sin) ** 2 + p1.map(math.cos) * p2.map(math.cos) * (dlambda / 2).map(math.sin) ** 2
    c = 2 * a.map(math.sqrt).map(math.asin)
    return r * c


def apply_fraud_rules(df: pd.DataFrame, cfg: LabelerConfig | None = None) -> pd.DataFrame:
    cfg = cfg or LabelerConfig()
    df = _normalize_input(df)
    df = df.sort_values(["_user_id", "_timestamp"], kind="mergesort").reset_index(drop=True)

    df["is_fraud_rule"] = 0
    df["fraud_reasons"] = ""

    g = df.groupby("_user_id", dropna=False)
    prev_amount = g["_amount"].shift(1)
    prev_time = g["_timestamp"].shift(1)
    time_diff_hours = (df["_timestamp"] - prev_time).dt.total_seconds() / 3600.0

    # A: Card testing burst then large purchase.
    small_txn = df["_amount"].lt(cfg.tiny_amt_threshold)
    small_24h_count = (
        small_txn.astype(int)
        .groupby(df["_user_id"])
        .rolling(f"{cfg.card_test_lookback_hours}h", on=df["_timestamp"])  # type: ignore[arg-type]
        .sum()
        .reset_index(level=0, drop=True)
    )
    card_test = (
        df["_amount"].gt(cfg.card_test_large_threshold)
        & prev_amount.lt(cfg.tiny_amt_threshold)
        & time_diff_hours.le(cfg.card_test_lookback_hours)
        & small_24h_count.ge(2)
    )

    # B: Velocity spender.
    velocity_count = (
        df.assign(_one=1)
        .set_index("_timestamp")
        .groupby("_user_id")["_one"]
        .rolling(cfg.velocity_window)
        .count()
        .reset_index(level=0, drop=True)
        .rename("_velocity_count")
    )
    df = df.join(velocity_count)
    velocity = df["_velocity_count"].gt(cfg.velocity_txn_count_threshold)

    # C: Impossible travel.
    prev_lat = g["_lat"].shift(1)
    prev_lon = g["_lon"].shift(1)
    valid_geo = prev_lat.notna() & prev_lon.notna() & df["_lat"].notna() & df["_lon"].notna() & time_diff_hours.gt(0)
    speed = pd.Series(0.0, index=df.index)
    if valid_geo.any():
        dist = _haversine_km(prev_lat[valid_geo], prev_lon[valid_geo], df.loc[valid_geo, "_lat"], df.loc[valid_geo, "_lon"])
        speed.loc[valid_geo] = dist / time_diff_hours[valid_geo]
    impossible = speed.gt(cfg.impossible_travel_kmh)

    # D: High risk MCC escalation.
    mcc = df["_mcc"].str.strip()
    high_risk_mcc = mcc.isin(cfg.high_risk_mccs) & df["_amount"].gt(cfg.high_risk_mcc_threshold)

    rules = {
        "CARD_TESTING": card_test,
        "VELOCITY_SPENDER": velocity,
        "IMPOSSIBLE_TRAVEL": impossible,
        "HIGH_RISK_MCC": high_risk_mcc,
    }

    for reason, mask in rules.items():
        df.loc[mask, "is_fraud_rule"] = 1
        df.loc[mask, "fraud_reasons"] = df.loc[mask, "fraud_reasons"].mask(
            df.loc[mask, "fraud_reasons"].eq(""), reason
        ).where(df.loc[mask, "fraud_reasons"].eq(""), df.loc[mask, "fraud_reasons"] + "|" + reason)

    # If generator already has label, keep both and expose a consensus label.
    if "Is_Fraud" in df.columns:
        df["is_fraud_generator"] = df["Is_Fraud"].astype(int)
        df["is_fraud_consensus"] = ((df["is_fraud_generator"] == 1) | (df["is_fraud_rule"] == 1)).astype(int)

    return df.drop(columns=[c for c in ["_velocity_count"] if c in df.columns])


def label_file(input_path: str, output_path: str) -> None:
    in_df = pd.read_json(input_path)
    out_df = apply_fraud_rules(in_df)
    if output_path.endswith(".json"):
        out_df.to_json(output_path, orient="records", indent=2, date_format="iso")
    else:
        out_df.to_csv(output_path, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Label synthraGen transactions with deterministic fraud rules.")
    parser.add_argument("--input", default="test_transactions.json", help="Input JSON transaction file")
    parser.add_argument("--output", default="labeled_transactions.csv", help="Output labeled file (.csv or .json)")
    args = parser.parse_args()
    label_file(args.input, args.output)
    print(f"Labeling complete: {args.output}")
