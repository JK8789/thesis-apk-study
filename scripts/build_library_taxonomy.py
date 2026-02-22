#!/usr/bin/env python3
from __future__ import annotations
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
LIBS = BASE / "results" / "libs_longest" / "libs_per_app_long.csv"
DEEP = BASE / "results" / "libs_longest" / "keyword_deep_hits.csv"
OUT = BASE / "data" / "meta"
OUT.mkdir(parents=True, exist_ok=True)

def classify(prefix: str) -> str:
    p = (prefix or "").lower()
    # order matters: more specific first
    if "captcha" in p or "geetest" in p or "seon" in p or "fraud" in p or "risk" in p:
        return "anti_fraud"
    if ".ads" in p or "ads" in p or "adservice" in p or "admob" in p or "monetization" in p:
        return "ads"
    if "pay" in p or "payment" in p or "sbp" in p:
        return "payments"
    if "tracker" in p or "analytics" in p or "appmetrica" in p or "metric" in p:
        return "analytics"
    if "push" in p or "messaging" in p or "fcm" in p:
        return "push"
    if "crash" in p or "sentry" in p or "bugsnag" in p or "firebasecrash" in p:
        return "crash"
    if "net" in p or "okhttp" in p or "cronet" in p:
        return "networking"
    return "other"

def main():
    libs = pd.read_csv(LIBS)
    deep = pd.read_csv(DEEP)

    # combine library prefixes + deep prefixes
    a = libs[["library_prefix"]].rename(columns={"library_prefix":"prefix"})
    b = deep[["prefix"]].copy()
    allp = pd.concat([a,b], ignore_index=True).dropna()
    allp["prefix"] = allp["prefix"].astype(str)

    tax = pd.DataFrame({"prefix": sorted(allp["prefix"].unique())})
    tax["type_auto"] = tax["prefix"].map(classify)

    out_path = OUT / "library_taxonomy_auto.csv"
    tax.to_csv(out_path, index=False)
    print("OK wrote", out_path, "rows=", len(tax))
    print(tax["type_auto"].value_counts().to_string())

if __name__ == "__main__":
    main()

