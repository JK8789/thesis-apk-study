#!/usr/bin/env python3
import csv
import hashlib
import os
import sys
from pathlib import Path

try:
    from androguard.core.apk import APK
except Exception as e:
    print("ERROR: androguard not available. Install/enable it in your venv.", file=sys.stderr)
    raise

# Android "dangerous" (runtime) permissions list for API 34+ to count and list dangerous_permissions.
# Source: merail/permissions-lists runtime_permissions.xml (space-separated list). :contentReference[oaicite:3]{index=3}
DANGEROUS_PERMS = {
    "android.permission.ACCEPT_HANDOVER",
    "android.permission.ACCESS_BACKGROUND_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_MEDIA_LOCATION",
    "android.permission.ACTIVITY_RECOGNITION",
    "com.android.voicemail.permission.ADD_VOICEMAIL",
    "android.permission.ANSWER_PHONE_CALLS",
    "android.permission.BLUETOOTH_ADVERTISE",
    "android.permission.BLUETOOTH_CONNECT",
    "android.permission.BLUETOOTH_SCAN",
    "android.permission.BODY_SENSORS",
    "android.permission.BODY_SENSORS_BACKGROUND",
    "android.permission.CALL_PHONE",
    "android.permission.CAMERA",
    "android.permission.GET_ACCOUNTS",
    "android.permission.NEARBY_WIFI_DEVICES",
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.PROCESS_OUTGOING_CALLS",
    "android.permission.READ_CALENDAR",
    "android.permission.READ_CALL_LOG",
    "android.permission.READ_CONTACTS",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.READ_MEDIA_AUDIO",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.READ_MEDIA_VISUAL_USER_SELECTED",
    "android.permission.READ_PHONE_NUMBERS",
    "android.permission.READ_PHONE_STATE",
    "android.permission.READ_SMS",
    "android.permission.RECEIVE_MMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.RECEIVE_WAP_PUSH",
    "android.permission.RECORD_AUDIO",
    "android.permission.SEND_SMS",
    "android.permission.USE_SIP",
    "android.permission.UWB_RANGING",
    "android.permission.WRITE_CALENDAR",
    "android.permission.WRITE_CALL_LOG",
    "android.permission.WRITE_CONTACTS",
    "android.permission.WRITE_EXTERNAL_STORAGE",
}

# Convenience “sensitive buckets” (subset of dangerous)
LOCATION = {
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_BACKGROUND_LOCATION",
}
CONTACTS = {"android.permission.READ_CONTACTS", "android.permission.WRITE_CONTACTS", "android.permission.GET_ACCOUNTS"}
SMS = {"android.permission.SEND_SMS", "android.permission.RECEIVE_SMS", "android.permission.READ_SMS", "android.permission.RECEIVE_MMS", "android.permission.RECEIVE_WAP_PUSH"}
PHONE = {"android.permission.READ_PHONE_STATE", "android.permission.READ_PHONE_NUMBERS", "android.permission.CALL_PHONE", "android.permission.ANSWER_PHONE_CALLS", "android.permission.USE_SIP"}
CALLLOG = {"android.permission.READ_CALL_LOG", "android.permission.WRITE_CALL_LOG", "android.permission.PROCESS_OUTGOING_CALLS"}
MEDIA_STORAGE = {
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.READ_MEDIA_AUDIO",
    "android.permission.READ_MEDIA_VISUAL_USER_SELECTED",
    "android.permission.ACCESS_MEDIA_LOCATION",
}
BLUETOOTH = {"android.permission.BLUETOOTH_CONNECT", "android.permission.BLUETOOTH_SCAN", "android.permission.BLUETOOTH_ADVERTISE"}
SENSORS = {"android.permission.BODY_SENSORS", "android.permission.BODY_SENSORS_BACKGROUND"}
NOTIFS = {"android.permission.POST_NOTIFICATIONS"}
NEARBY_WIFI = {"android.permission.NEARBY_WIFI_DEVICES"}

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def read_apps_csv(apps_csv: Path):
    """
    Supports:
    - header with columns: group, apk_path, pair_id (names can vary a bit)
    - no header: [0]=group, [1]=apk_path, [2]=pair_id
    """
    with apps_csv.open("r", encoding="utf-8", newline="") as f:
        sample = f.read(2048)
        f.seek(0)

        has_header = ("pair_id" in sample.lower()) or ("apk_path" in sample.lower()) or ("group" in sample.lower())
        if has_header:
            r = csv.DictReader(f)
            for row in r:
                # normalize keys
                keys = {k.lower().strip(): k for k in row.keys() if k}
                def get(*names):
                    for n in names:
                        if n in keys:
                            return (row.get(keys[n]) or "").strip()
                    return ""
                group = get("group", "region", "country")
                apk_path = get("apk_path", "path", "apk", "file")
                pair_id = get("pair_id", "pair", "pairid", "pair-id")
                yield group, apk_path, pair_id
        else:
            r = csv.reader(f)
            for row in r:
                if not row or len(row) < 3:
                    continue
                group = row[0].strip()
                apk_path = row[1].strip()
                pair_id = row[2].strip()
                yield group, apk_path, pair_id

def main(apps_csv: Path, out_csv: Path):
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "pair_id",
        "group",
        "apk_path",
        "apk_file",
        "sha256",
        "pkg_name",
        "versionCode",
        "versionName",
        "total_permissions_count",
        "dangerous_permissions_count",
        "dangerous_permissions",
        "all_permissions",
        # sensitive bucket flags (helpful for thesis tables)
        "has_location",
        "has_camera",
        "has_microphone",
        "has_contacts",
        "has_sms",
        "has_phone",
        "has_calllog",
        "has_media_storage",
        "has_bluetooth",
        "has_sensors",
        "has_notifications",
        "has_nearby_wifi",
        "error",
    ]

    with out_csv.open("w", encoding="utf-8", newline="") as o:
        w = csv.DictWriter(o, fieldnames=fieldnames)
        w.writeheader()

        count = 0
        for group, apk_path_str, pair_id in read_apps_csv(apps_csv):
            apk_path = Path(apk_path_str)
            row_out = {k: "" for k in fieldnames}
            row_out["pair_id"] = pair_id
            row_out["group"] = group
            row_out["apk_path"] = str(apk_path)
            row_out["apk_file"] = apk_path.name

            try:
                if not apk_path.exists():
                    raise FileNotFoundError(f"APK not found: {apk_path}")

                row_out["sha256"] = sha256_file(apk_path)

                a = APK(str(apk_path))
                row_out["pkg_name"] = a.get_package() or ""
                row_out["versionCode"] = a.get_androidversion_code() or ""
                row_out["versionName"] = a.get_androidversion_name() or ""

                perms = sorted(set(a.get_permissions() or []))
                dangerous = [p for p in perms if p in DANGEROUS_PERMS]

                row_out["total_permissions_count"] = str(len(perms))
                row_out["dangerous_permissions_count"] = str(len(dangerous))
                row_out["all_permissions"] = ";".join(perms)
                row_out["dangerous_permissions"] = ";".join(dangerous)

                # bucket flags
                s = set(dangerous)
                row_out["has_location"] = "1" if s.intersection(LOCATION) else "0"
                row_out["has_camera"] = "1" if "android.permission.CAMERA" in s else "0"
                row_out["has_microphone"] = "1" if "android.permission.RECORD_AUDIO" in s else "0"
                row_out["has_contacts"] = "1" if s.intersection(CONTACTS) else "0"
                row_out["has_sms"] = "1" if s.intersection(SMS) else "0"
                row_out["has_phone"] = "1" if s.intersection(PHONE) else "0"
                row_out["has_calllog"] = "1" if s.intersection(CALLLOG) else "0"
                row_out["has_media_storage"] = "1" if s.intersection(MEDIA_STORAGE) else "0"
                row_out["has_bluetooth"] = "1" if s.intersection(BLUETOOTH) else "0"
                row_out["has_sensors"] = "1" if s.intersection(SENSORS) else "0"
                row_out["has_notifications"] = "1" if s.intersection(NOTIFS) else "0"
                row_out["has_nearby_wifi"] = "1" if s.intersection(NEARBY_WIFI) else "0"

            except Exception as e:
                row_out["error"] = str(e)

            w.writerow(row_out)
            count += 1

    print(f"Wrote: {out_csv} (rows={count})")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        apps = Path("apps.csv")
        out = Path("local/extracted_local_features.csv")
    elif len(sys.argv) == 3:
        apps = Path(sys.argv[1])
        out = Path(sys.argv[2])
    else:
        print("Usage: extracte_local_features.py [apps.csv local/extracted_local_features.csv]", file=sys.stderr)
        sys.exit(2)

    main(apps, out)
