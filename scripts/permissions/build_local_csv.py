#!/usr/bin/env python3
import csv
import json
from pathlib import Path

APPS_CSV = Path("data/meta/apps.csv")
MANIFEST_DIR = Path("results/manifest")
OUT_CSV = Path("results/local/local_from_manifest.csv")

LOCAL_FIELDS = [
    "package",
    "version_code",
    "version_name",
    "min_sdk",
    "target_sdk",
    "max_sdk",
    "perm_count_local",
    "activities_local",
    "services_local",
    "receivers_local",
    "providers_local",
    "exported_act_true",
    "exported_srv_true",
    "exported_rcv_true",
    "exported_prv_true",
    "is_debuggable",
]

def safe_int(x):
    try:
        if x is None or x == "":
            return ""
        return int(x)
    except Exception:
        return ""

def main():
    rows_out = []
    with APPS_CSV.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            sha = (row.get("sha256") or "").strip().upper()
            if not sha:
                continue

            mf_path = MANIFEST_DIR / f"{sha}.json"
            local = {k: "" for k in LOCAL_FIELDS}
            local["sha256"] = sha

            if mf_path.exists():
                obj = json.loads(mf_path.read_text(encoding="utf-8"))

                local["package"] = obj.get("package") or ""
                local["version_code"] = obj.get("version_code") if obj.get("version_code") is not None else ""
                local["version_name"] = obj.get("version_name") or ""

                sdk = obj.get("sdk") or {}
                local["min_sdk"] = sdk.get("min_sdk") if sdk.get("min_sdk") is not None else ""
                local["target_sdk"] = sdk.get("target_sdk") if sdk.get("target_sdk") is not None else ""
                local["max_sdk"] = sdk.get("max_sdk") if sdk.get("max_sdk") is not None else ""

                local["perm_count_local"] = obj.get("permissions_count") if obj.get("permissions_count") is not None else ""

                comps = obj.get("components") or {}
                local["activities_local"] = comps.get("activities") if comps.get("activities") is not None else ""
                local["services_local"] = comps.get("services") if comps.get("services") is not None else ""
                local["receivers_local"] = comps.get("receivers") if comps.get("receivers") is not None else ""
                local["providers_local"] = comps.get("providers") if comps.get("providers") is not None else ""


                exported = (
                    obj.get("exported_components_explicit_true")
                    or obj.get("exported_components_true")
                    or obj.get("exported_components")
                    or {}
                )
                local["exported_act_true"] = exported.get("activities") if exported.get("activities") is not None else ""
                local["exported_srv_true"] = exported.get("services") if exported.get("services") is not None else ""
                local["exported_rcv_true"] = exported.get("receivers") if exported.get("receivers") is not None else ""
                local["exported_prv_true"] = exported.get("providers") if exported.get("providers") is not None else ""

                dbg = obj.get("is_debuggable")
                local["is_debuggable"] = "" if dbg is None else str(bool(dbg))

            rows_out.append(local)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sha256"] + LOCAL_FIELDS)
        w.writeheader()
        for row in rows_out:

            for k in ["version_code","min_sdk","target_sdk","max_sdk",
                      "perm_count_local","activities_local","services_local","receivers_local","providers_local",
                      "exported_act_true","exported_srv_true","exported_rcv_true","exported_prv_true"]:
                row[k] = safe_int(row.get(k, ""))
            w.writerow(row)

    print(f"Wrote {OUT_CSV}")

if __name__ == "__main__":
    main()

