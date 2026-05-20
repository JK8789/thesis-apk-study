#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET

from androguard.core.apk import APK

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_CSV = BASE_DIR / "results" / "baseline" / "apps_baseline.csv"
OUT_DIR = BASE_DIR / "results" / "local"

OUT_SUMMARY = OUT_DIR / "manifest_permissions_components_summary.csv"
OUT_PERMISSION_LIST = OUT_DIR / "manifest_permission_list.csv"
OUT_COMPONENT_LIST = OUT_DIR / "manifest_component_list.csv"

ANDROID_NS = "http://schemas.android.com/apk/res/android"
NS_NAME = f"{{{ANDROID_NS}}}name"
NS_EXPORTED = f"{{{ANDROID_NS}}}exported"

# Fixed study reference for dangerous permissions
DANGEROUS_PERMISSIONS = {
    "android.permission.READ_CALENDAR",
    "android.permission.WRITE_CALENDAR",
    "android.permission.CAMERA",
    "android.permission.READ_CONTACTS",
    "android.permission.WRITE_CONTACTS",
    "android.permission.GET_ACCOUNTS",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_BACKGROUND_LOCATION",
    "android.permission.RECORD_AUDIO",
    "android.permission.READ_PHONE_STATE",
    "android.permission.READ_PHONE_NUMBERS",
    "android.permission.CALL_PHONE",
    "android.permission.ANSWER_PHONE_CALLS",
    "android.permission.ADD_VOICEMAIL",
    "android.permission.USE_SIP",
    "android.permission.PROCESS_OUTGOING_CALLS",
    "android.permission.BODY_SENSORS",
    "android.permission.BODY_SENSORS_BACKGROUND",
    "android.permission.ACTIVITY_RECOGNITION",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.READ_MEDIA_AUDIO",
    "android.permission.NEARBY_WIFI_DEVICES",
    "android.permission.BLUETOOTH_SCAN",
    "android.permission.BLUETOOTH_CONNECT",
    "android.permission.BLUETOOTH_ADVERTISE",
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.READ_CALL_LOG",
    "android.permission.WRITE_CALL_LOG",
    "android.permission.SEND_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.READ_SMS",
    "android.permission.RECEIVE_WAP_PUSH",
    "android.permission.RECEIVE_MMS",
}

def read_apps(path: Path) -> List[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            apk_path = (row.get("apk_path") or "").strip()
            sha256 = (row.get("sha256") or "").strip().upper()
            if not apk_path or not sha256:
                continue
            rows.append(row)
    return rows

def normalize_component_name(name: str, package: str) -> str:
    if not name:
        return ""
    name = name.strip()
    if name.startswith("."):
        return package + name
    if "." not in name:
        return package + "." + name
    return name

def get_attr(elem: ET.Element, attr_local_name: str) -> str:
    # try namespaced attr first
    val = elem.get(f"{{{ANDROID_NS}}}{attr_local_name}")
    if val is not None:
        return val
    # fallback for packed/non-standard manifests
    val = elem.get(attr_local_name)
    if val is not None:
        return val
    # last fallback: attrs ending with local name
    for k, v in elem.attrib.items():
        if k.endswith(attr_local_name):
            return v
    return ""

def component_elements(manifest_root: ET.Element) -> ET.Element:
    app = manifest_root.find("application")
    return app

def collect_component_rows(manifest_root: ET.Element, package: str) -> List[dict]:
    app = component_elements(manifest_root)
    if app is None:
        return []

    rows: List[dict] = []

    tag_to_type = {
        "activity": "activity",
        "activity-alias": "activity",
        "service": "service",
        "receiver": "receiver",
        "provider": "provider",
    }

    for child in app:
        tag = child.tag.split("}")[-1]
        if tag not in tag_to_type:
            continue

        comp_type = tag_to_type[tag]
        raw_name = get_attr(child, "name")
        comp_name = normalize_component_name(raw_name, package)
        exported_raw = get_attr(child, "exported").strip().lower()
        intent_filter_present = any(
            c.tag.split("}")[-1] == "intent-filter" for c in child
        )

        # Android rule:
        # if android:exported explicitly set -> use it
        # otherwise components with intent-filters were historically exposed by default
        # for this extraction we keep:
        # exported_true = only explicit true
        # and separately store whether intent-filter exists
        exported_true = exported_raw == "true"

        rows.append(
            {
                "component_name": comp_name,
                "component_type": comp_type,
                "exported_true": exported_true,
                "intent_filter_present": intent_filter_present,
                "exported_raw": exported_raw,
            }
        )

    return rows

def semicolon_join(values: List[str]) -> str:
    return ";".join(sorted(dict.fromkeys(v for v in values if v)))

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    apps = read_apps(INPUT_CSV)

    summary_rows = []
    permission_rows = []
    component_rows = []

    for row in apps:
        region = (row.get("region") or "").strip()
        category = (row.get("category") or "").strip()
        pair_id = (row.get("pair_id") or "").strip()
        app_name = (row.get("app_name") or "").strip()
        apk_path = (row.get("apk_path") or "").strip()
        sha256 = (row.get("sha256") or "").strip().upper()

        print(f"[EXTRACT] {sha256}  {app_name}")

        try:
            apk = APK(apk_path)
            package = (apk.get_package() or row.get("package") or "").strip()

            permissions = sorted(set(apk.get_permissions() or []))
            dangerous_permissions = sorted(
                p for p in permissions if p in DANGEROUS_PERMISSIONS
            )

            manifest_xml = apk.get_android_manifest_xml()
            if manifest_xml is None:
                raise RuntimeError("AndroidManifest.xml could not be parsed")

            # Ensure we work with stdlib ElementTree Element
            if isinstance(manifest_xml, ET.Element):
                root = manifest_xml
            else:
                # lxml element also works for most stdlib-style access
                root = manifest_xml

            comps = collect_component_rows(root, package)

            all_activities = [c["component_name"] for c in comps if c["component_type"] == "activity"]
            all_services = [c["component_name"] for c in comps if c["component_type"] == "service"]
            all_receivers = [c["component_name"] for c in comps if c["component_type"] == "receiver"]
            all_providers = [c["component_name"] for c in comps if c["component_type"] == "provider"]

            exported_activities = [c["component_name"] for c in comps if c["component_type"] == "activity" and c["exported_true"]]
            exported_services = [c["component_name"] for c in comps if c["component_type"] == "service" and c["exported_true"]]
            exported_receivers = [c["component_name"] for c in comps if c["component_type"] == "receiver" and c["exported_true"]]
            exported_providers = [c["component_name"] for c in comps if c["component_type"] == "provider" and c["exported_true"]]

            summary_rows.append(
                {
                    "region": region,
                    "category": category,
                    "pair_id": pair_id,
                    "app_name": app_name,
                    "package": package,
                    "sha256": sha256,

                    "requested_permissions_count": len(permissions),
                    "requested_permissions_list": semicolon_join(permissions),

                    "dangerous_permissions_count": len(dangerous_permissions),
                    "dangerous_permissions_list": semicolon_join(dangerous_permissions),

                    "activities_all_count": len(all_activities),
                    "activities_all_list": semicolon_join(all_activities),
                    "activities_exported_count": len(exported_activities),
                    "activities_exported_list": semicolon_join(exported_activities),

                    "services_all_count": len(all_services),
                    "services_all_list": semicolon_join(all_services),
                    "services_exported_count": len(exported_services),
                    "services_exported_list": semicolon_join(exported_services),

                    "receivers_all_count": len(all_receivers),
                    "receivers_all_list": semicolon_join(all_receivers),
                    "receivers_exported_count": len(exported_receivers),
                    "receivers_exported_list": semicolon_join(exported_receivers),

                    "providers_all_count": len(all_providers),
                    "providers_all_list": semicolon_join(all_providers),
                    "providers_exported_count": len(exported_providers),
                    "providers_exported_list": semicolon_join(exported_providers),
                }
            )

            for perm in permissions:
                permission_rows.append(
                    {
                        "region": region,
                        "category": category,
                        "pair_id": pair_id,
                        "app_name": app_name,
                        "package": package,
                        "sha256": sha256,
                        "permission": perm,
                        "is_dangerous": "true" if perm in DANGEROUS_PERMISSIONS else "false",
                    }
                )

            for comp in comps:
                component_rows.append(
                    {
                        "region": region,
                        "category": category,
                        "pair_id": pair_id,
                        "app_name": app_name,
                        "package": package,
                        "sha256": sha256,
                        "component_name": comp["component_name"],
                        "component_type": comp["component_type"],
                        "exported_true": "true" if comp["exported_true"] else "false",
                        "intent_filter_present": "true" if comp["intent_filter_present"] else "false",
                    }
                )

        except Exception as e:
            print(f"[ERROR] {sha256} {app_name}: {e}")

    summary_fields = [
        "region", "category", "pair_id", "app_name", "package", "sha256",
        "requested_permissions_count", "requested_permissions_list",
        "dangerous_permissions_count", "dangerous_permissions_list",
        "activities_all_count", "activities_all_list",
        "activities_exported_count", "activities_exported_list",
        "services_all_count", "services_all_list",
        "services_exported_count", "services_exported_list",
        "receivers_all_count", "receivers_all_list",
        "receivers_exported_count", "receivers_exported_list",
        "providers_all_count", "providers_all_list",
        "providers_exported_count", "providers_exported_list",
    ]

    permission_fields = [
        "region", "category", "pair_id", "app_name", "package", "sha256",
        "permission", "is_dangerous",
    ]

    component_fields = [
        "region", "category", "pair_id", "app_name", "package", "sha256",
        "component_name", "component_type", "exported_true", "intent_filter_present",
    ]

    with OUT_SUMMARY.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=summary_fields)
        w.writeheader()
        w.writerows(summary_rows)

    with OUT_PERMISSION_LIST.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=permission_fields)
        w.writeheader()
        w.writerows(permission_rows)

    with OUT_COMPONENT_LIST.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=component_fields)
        w.writeheader()
        w.writerows(component_rows)

    print(f"Wrote {OUT_SUMMARY}")
    print(f"Wrote {OUT_PERMISSION_LIST}")
    print(f"Wrote {OUT_COMPONENT_LIST}")

if __name__ == "__main__":
    main()
