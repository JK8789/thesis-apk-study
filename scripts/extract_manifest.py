#!/usr/bin/env python3
import csv
import json
import os
import sys
from pathlib import Path

from lxml import etree
from androguard.core.apk import APK


try:
    from loguru import logger
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
except Exception:
    pass

APPS_CSV = Path("data/meta/apps.csv")
OUT_DIR = Path("results/manifest")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ANDROID_NS = "http://schemas.android.com/apk/res/android"


def _attr(elem, key: str):

    if elem is None:
        return None
    v = elem.get(f"{{{ANDROID_NS}}}{key}")
    if v is not None:
        return v
    return elem.get(key)


def _load_manifest_xml(apk: APK):


    try:
        m = apk.get_android_manifest_xml()
        if m is None:
            return None
        if isinstance(m, (bytes, bytearray)):
            return etree.fromstring(bytes(m))
        if isinstance(m, str):
            return etree.fromstring(m.encode("utf-8", errors="ignore"))

        return m
    except Exception:
        pass


    try:
        from androguard.core.axml import AXMLPrinter  
        raw = apk.get_file("AndroidManifest.xml")
        if not raw:
            return None
        xml_bytes = AXMLPrinter(raw).get_xml()
        if not xml_bytes:
            return None
        if isinstance(xml_bytes, str):
            xml_bytes = xml_bytes.encode("utf-8", errors="ignore")
        return etree.fromstring(xml_bytes)
    except Exception:
        return None


def _parse_permissions_from_manifest(manifest_root):
    perms = []
    if manifest_root is None:
        return perms

    for tag in ("uses-permission", "uses-permission-sdk-23"):
        for el in manifest_root.findall(tag):
            name = _attr(el, "name")
            if name:
                perms.append(name)


    return sorted(set(perms))


def _get_sdk_versions(apk: APK, manifest_root):
    def safe_int(x):
        if x is None:
            return None
        s = str(x).strip()
        if s == "":
            return None
        try:
            return int(s)
        except Exception:
            return None

    min_sdk = None
    target_sdk = None
    max_sdk = None


    for fn, var in [
        ("get_min_sdk_version", "min"),
        ("get_target_sdk_version", "target"),
        ("get_max_sdk_version", "max"),
    ]:
        try:
            val = getattr(apk, fn)()
            if var == "min":
                min_sdk = safe_int(val)
            elif var == "target":
                target_sdk = safe_int(val)
            else:
                max_sdk = safe_int(val)
        except Exception:
            pass


    if manifest_root is not None:
        uses_sdk = manifest_root.find("uses-sdk")
        if uses_sdk is not None:
            if min_sdk is None:
                min_sdk = safe_int(_attr(uses_sdk, "minSdkVersion"))
            if target_sdk is None:
                target_sdk = safe_int(_attr(uses_sdk, "targetSdkVersion"))
            if max_sdk is None:
                max_sdk = safe_int(_attr(uses_sdk, "maxSdkVersion"))

    return min_sdk, target_sdk, max_sdk


def _count_components_from_manifest(manifest_root):
    """
    Counts declared components under <application>.
    Includes activity-alias in activities.
    """
    if manifest_root is None:
        return None

    app = manifest_root.find("application")
    if app is None:
        return None

    activities = len(app.findall("activity")) + len(app.findall("activity-alias"))
    services = len(app.findall("service"))
    receivers = len(app.findall("receiver"))
    providers = len(app.findall("provider"))

    return {
        "activities": activities,
        "services": services,
        "receivers": receivers,
        "providers": providers,
    }


def _count_exported_true_from_manifest(manifest_root):
    """
    Counts components explicitly having android:exported="true".
    """
    if manifest_root is None:
        return None

    app = manifest_root.find("application")
    if app is None:
        return None

    def count_tag(tag):
        c = 0
        for el in app.findall(tag):
            v = _attr(el, "exported")
            if v is not None and str(v).strip().lower() == "true":
                c += 1
        return c

    return {
        "activities": count_tag("activity") + count_tag("activity-alias"),
        "services": count_tag("service"),
        "receivers": count_tag("receiver"),
        "providers": count_tag("provider"),
    }


def _get_debuggable_from_manifest(manifest_root):
    if manifest_root is None:
        return None
    app = manifest_root.find("application")
    if app is None:
        return None
    v = _attr(app, "debuggable")
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("true", "1"):
        return True
    if s in ("false", "0"):
        return False
    return None


def main():
    if not APPS_CSV.exists():
        print(f"ERROR: missing {APPS_CSV}", file=sys.stderr)
        sys.exit(1)

    with APPS_CSV.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)

    for row in rows:
        sha = row.get("sha256", "").strip().upper()
        apk_path = row.get("apk_path", "").strip()
        if not sha or not apk_path:
            continue

        print(f"[MANIFEST] {sha}", flush=True)

        out_path = OUT_DIR / f"{sha}.json"

        if not os.path.isfile(apk_path):
            payload = {"sha256": sha, "apk_path": apk_path, "error": "missing_apk_file"}
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            continue

        payload = {"sha256": sha, "apk_path": apk_path}
        try:
            apk = APK(apk_path)
            manifest_root = _load_manifest_xml(apk)

            # package + versions
            try:
                payload["package"] = apk.get_package()
            except Exception:
                payload["package"] = None

            try:
                payload["version_code"] = apk.get_androidversion_code()
            except Exception:
                payload["version_code"] = None

            try:
                payload["version_name"] = apk.get_androidversion_name()
            except Exception:
                payload["version_name"] = None

            # SDK
            min_sdk, target_sdk, max_sdk = _get_sdk_versions(apk, manifest_root)
            payload["sdk"] = {"min_sdk": min_sdk, "target_sdk": target_sdk, "max_sdk": max_sdk}


            perms = []
            try:
                perms = apk.get_permissions() or []
            except Exception:
                perms = []

            if not perms:
                perms = _parse_permissions_from_manifest(manifest_root)


            perms = sorted(set(perms))
            payload["permissions"] = perms
            payload["permissions_count"] = len(perms)

            # components + exported
            comps = _count_components_from_manifest(manifest_root)
            if comps is None:

                try:
                    comps = {
                        "activities": len(apk.get_activities() or []),
                        "services": len(apk.get_services() or []),
                        "receivers": len(apk.get_receivers() or []),
                        "providers": len(apk.get_providers() or []),
                    }
                except Exception:
                    comps = {"activities": 0, "services": 0, "receivers": 0, "providers": 0}
            payload["components"] = comps

            exported_true = _count_exported_true_from_manifest(manifest_root)
            if exported_true is None:
                exported_true = {"activities": 0, "services": 0, "receivers": 0, "providers": 0}
            payload["exported_components_explicit_true"] = exported_true

            payload["is_debuggable"] = _get_debuggable_from_manifest(manifest_root)

        except Exception as e:
            payload["error"] = f"{type(e).__name__}: {e}"

        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

