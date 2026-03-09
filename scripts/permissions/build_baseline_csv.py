#!/usr/bin/env python3
import csv
import json
import os
import datetime
from typing import Any, Dict, Optional

APPS_CSV = "data/meta/apps.csv"
MAN_DIR = "results/manifest"
VT_DIR = "results/vt/file"
OUT_CSV = "results/baseline/apps_baseline.csv"


def load_json(path: str) -> Optional[Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def epoch_to_iso(ts):
    if ts is None:
        return None
    try:
        ts_int = int(ts)
        return datetime.datetime.fromtimestamp(ts_int, datetime.UTC).isoformat().replace("+00:00", "Z")
    except Exception:
        return str(ts)


def get_vt_obj(vt_json: Any) -> Dict[str, Any]:

    if isinstance(vt_json, list) and vt_json:
        if isinstance(vt_json[0], dict):
            return vt_json[0]
    return {}


def count_vt_dangerous_perms(vt_andro: Dict[str, Any]) -> int:

    pd = vt_andro.get("permission_details", {})
    if not isinstance(pd, dict):
        return 0
    c = 0
    for _, info in pd.items():
        if isinstance(info, dict):
            ptype = str(info.get("permission_type", "")).lower()
            if "dangerous" in ptype:
                c += 1
    return c


def main() -> None:
    fieldnames = [
        # labels from apps.csv
        "region", "category", "pair_id", "app_name",
        "apk_path", "sha256",

        # local manifest
        "package",
        "version_code", "version_name",
        "min_sdk", "target_sdk", "max_sdk",
        "perm_count_local",
        "activities_local", "services_local", "receivers_local", "providers_local",
        "exported_act_true", "exported_srv_true", "exported_rcv_true", "exported_prv_true",
        "is_debuggable",

        # VirusTotal
        "vt_last_analysis_date",
        "vt_malicious", "vt_suspicious", "vt_harmless", "vt_undetected",
        "vt_perm_count", "vt_dangerous_perm_count",
    ]

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)

    with open(APPS_CSV, newline="", encoding="utf-8") as f_in, open(OUT_CSV, "w", newline="", encoding="utf-8") as f_out:
        r = csv.DictReader(f_in)
        w = csv.DictWriter(f_out, fieldnames=fieldnames)
        w.writeheader()

        for row in r:
            sha = (row.get("sha256") or "").strip().upper()
            if not sha:
                continue

            man_path = os.path.join(MAN_DIR, f"{sha}.json")
            vt_path = os.path.join(VT_DIR, f"{sha}.json")

            man = load_json(man_path) or {}
            vt_raw = load_json(vt_path)
            vt = get_vt_obj(vt_raw)

            # Local manifest fields
            sdk = man.get("sdk", {}) if isinstance(man.get("sdk", {}), dict) else {}
            comps = man.get("components", {}) if isinstance(man.get("components", {}), dict) else {}
            exp = man.get("exported_components_explicit_true", {}) if isinstance(man.get("exported_components_explicit_true", {}), dict) else {}

            # VT fields
            stats = vt.get("last_analysis_stats", {}) if isinstance(vt.get("last_analysis_stats", {}), dict) else {}
            vt_andro = vt.get("androguard", {}) if isinstance(vt.get("androguard", {}), dict) else {}

            vt_perm_count = None
            # vt_andro may have "permissions" list or permission_details keys
            if isinstance(vt_andro.get("permissions"), list):
                vt_perm_count = len(vt_andro.get("permissions"))
            elif isinstance(vt_andro.get("permission_details"), dict):
                vt_perm_count = len(vt_andro.get("permission_details"))

            out = {
                "region": row.get("region"),
                "category": row.get("category"),
                "pair_id": row.get("pair_id"),
                "app_name": row.get("app_name"),
                "apk_path": row.get("apk_path"),
                "sha256": sha,

                "package": man.get("package"),
                "version_code": man.get("version_code"),
                "version_name": man.get("version_name"),
                "min_sdk": sdk.get("min_sdk"),
                "target_sdk": sdk.get("target_sdk"),
                "max_sdk": sdk.get("max_sdk"),
                "perm_count_local": man.get("permissions_count"),

                "activities_local": comps.get("activities"),
                "services_local": comps.get("services"),
                "receivers_local": comps.get("receivers"),
                "providers_local": comps.get("providers"),

                "exported_act_true": exp.get("activities"),
                "exported_srv_true": exp.get("services"),
                "exported_rcv_true": exp.get("receivers"),
                "exported_prv_true": exp.get("providers"),

                "is_debuggable": man.get("is_debuggable"),

                "vt_last_analysis_date": epoch_to_iso(vt.get("last_analysis_date")),
                "vt_malicious": stats.get("malicious"),
                "vt_suspicious": stats.get("suspicious"),
                "vt_harmless": stats.get("harmless"),
                "vt_undetected": stats.get("undetected"),

                "vt_perm_count": vt_perm_count,
                "vt_dangerous_perm_count": count_vt_dangerous_perms(vt_andro),
            }

            w.writerow(out)

    print(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()

