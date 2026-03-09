#!/usr/bin/env python3
from __future__ import annotations
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
INP = BASE / "results" / "libs_longest" / "keyword_deep_hits.csv"
OUT = BASE / "results" / "libs_longest" / "keyword_deep_hits_typed.csv"

def classify(prefix: str) -> str:
    p = (prefix or "").lower()

    if any(x in p for x in ["geetest", "captcha", "recaptcha", "seon", "fraud", "risk", "threat", "fingerprint"]):
        return "anti_fraud"

    # payments: vendor names + safe tokens
    if any(x in p for x in ["stripe", "paypal", "adyen", "braintree", "klarna"]):
        return "payments"
    if any(x in p for x in ["payment", "payments", "billing", "vkpay", "sbpay", "samsungpay", "wallet", ".pay.", ".sbp.", ".paylibrary.", "pay."]):
        return "payments"

    # ads: avoid raw "ad" substring; use safe tokens
    if any(x in p for x in [".ads.", "admob", "doubleclick", "applovin", "ironsource", "adcolony",
                            "unity3d.ads", "facebook.ads", "yandex.mobile.ads", "google.android.gms.ads",
                            "miniappsads"]):
        return "ads"

    # analytics/attribution
    if any(x in p for x in ["adjust.sdk", "appmetrica", "firebase.analytics", "amplitude",
                            "mixpanel", "my.tracker", "flurry", "segment", "analytics", "tracker"]):
        return "analytics"

    if any(x in p for x in ["firebase.messaging", "onesignal", "pushwoosh", "push"]):
        return "push"

    if any(x in p for x in ["sentry", "bugsnag", "crashlytics", "firebase.crashlytics", "crash"]):
        return "crash"

    if any(x in p for x in ["okhttp", "retrofit", "cronet", "org.chromium.net", "network"]):
        return "networking"

    return "other"

def main():
    df = pd.read_csv(INP)
    df["type"] = df["prefix"].astype(str).map(classify)
    df.to_csv(OUT, index=False)
    print("OK wrote", OUT, "rows=", len(df))
    print(df["type"].value_counts().to_string())

if __name__ == "__main__":
    main()
