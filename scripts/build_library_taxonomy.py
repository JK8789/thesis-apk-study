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

    # Anti-fraud / captcha / risk
    if any(x in p for x in ["geetest", "captcha", "recaptcha", "seon", "fraud", "risk", "threat", "fingerprint"]):
        return "anti_fraud"

    # Payments (use vendor names + very specific payment tokens)
    if any(x in p for x in [
        "stripe",
        "paypal",
        "adyen",
        "braintree",
        "klarna",
    ]):
        return "payments"

    # Strong payment patterns (safer than "pay")
    if any(x in p for x in [
        "payment", "payments", "billing", "vkpay", "sbpay", "samsungpay", ".pay.", ".paylib", "googlepay", "applepay", ".paylibrary.", "pay.",
    ]):
        return "payments"

    # Ads (avoid raw "ad" or "ads" substring; require structure or known vendors)
    if any(x in p for x in [
        ".ads.",              # safest generic rule
        "admob",
        "doubleclick",
        "applovin",
        "ironsource",
        "adcolony",
        "unity3d.ads",
        "facebook.ads",
        "adservice",
        "yandex.mobile.ads",
        "miniappsads",
        "google.android.gms.ads",
    ]):
        return "ads"

    # Analytics / attribution / tracking (use vendors)
    if any(x in p for x in [
        "adjust.sdk",
        "appmetrica",
        "firebase.analytics",
        "amplitude",
        "mixpanel",
        "my.tracker",
        "flurry",
        "segment",
        "analytics",
        "tracker",
    ]):
        return "analytics"

    # Push / messaging
    if any(x in p for x in [
        "firebase.messaging",
        "push",
        "onesignal",
        "pushwoosh",
    ]):
        return "push"

    # Crash reporting
    if any(x in p for x in [
        "sentry",
        "bugsnag",
        "crashlytics",
        "crash",
        "firebase.crashlytics",
    ]):
        return "crash"

    # Networking (optional)
    if any(x in p for x in [
        "okhttp",
        "network",
        "retrofit",
        "cronet",
        "org.chromium.net",
    ]):
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

