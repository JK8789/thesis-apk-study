#!/usr/bin/env python3

import csv
from pathlib import Path


ROOT = Path("dataset2")
OUT = Path("dataset2.csv")


def read_text(path: Path):
    if path.exists():
        return path.read_text(encoding="utf-8", errors="ignore").strip()
    return None


def read_lines(path: Path):
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]


def parse_version_txt(path: Path):
    txt = read_text(path)
    version_code = None
    version_name = None

    if not txt:
        return version_code, version_name

    if "versionCode='" in txt:
        version_code = txt.split("versionCode='", 1)[1].split("'", 1)[0]

    if "versionName='" in txt:
        version_name = txt.split("versionName='", 1)[1].split("'", 1)[0]

    return version_code, version_name


def parse_summary(path: Path):
    result = {
        "requested_permissions_count": 0,
        "declared_permissions_count": 0,
        "activities_all": 0,
        "activities_exported": 0,
        "services_all": 0,
        "services_exported": 0,
        "receivers_all": 0,
        "receivers_exported": 0,
        "providers_all": 0,
        "providers_exported": 0,
    }

    txt = read_text(path)
    if not txt:
        return result

    for line in txt.splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k in result:
            try:
                result[k] = int(v)
            except ValueError:
                result[k] = 0

    return result


def parse_sha256(path: Path):
    txt = read_text(path)
    if not txt:
        return None
    return txt.split()[0]


def parse_cert_sha256(path: Path):
    txt = read_text(path)
    if not txt:
        return None

    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("Signer #1 certificate SHA-256 digest:"):
            return line.split(":", 1)[1].strip()

    if ":" not in txt and len(txt.strip()) >= 32:
        return txt.strip()

    return txt.strip()


def parse_size(path: Path):
    txt = read_text(path)
    if not txt:
        return None
    try:
        return int(txt)
    except ValueError:
        return None


def find_apk_filename(store_dir: Path):
    apks = sorted(store_dir.glob("*.apk"))
    return apks[0].name if apks else None


def load_store_record(package_dir: Path, store: str):
    store_dir = package_dir / store
    if not store_dir.exists():
        return None

    record = {
        "package": package_dir.name,
        "store": store,
        "apk_filename": find_apk_filename(store_dir),
        "versionCode": None,
        "versionName": None,
        "sha256": None,
        "signer_cert_sha256": None,
        "size_bytes": None,
        "requested_permissions_count": 0,
        "declared_permissions_count": 0,
        "activities_all": 0,
        "activities_exported": 0,
        "services_all": 0,
        "services_exported": 0,
        "receivers_all": 0,
        "receivers_exported": 0,
        "providers_all": 0,
        "providers_exported": 0,
        "_requested_permissions_set": set(),
    }

    version_code, version_name = parse_version_txt(store_dir / "version.txt")
    record["versionCode"] = version_code
    record["versionName"] = version_name
    record["sha256"] = parse_sha256(store_dir / "sha256.txt")
    record["signer_cert_sha256"] = parse_cert_sha256(store_dir / "cert_sha256.txt")
    record["size_bytes"] = parse_size(store_dir / "size_bytes.txt")

    summary = parse_summary(store_dir / "manifest_security_summary.txt")
    record.update(summary)

    requested_permissions = set(read_lines(store_dir / "requested_permissions.txt"))
    record["_requested_permissions_set"] = requested_permissions

    if requested_permissions and record["requested_permissions_count"] == 0:
        record["requested_permissions_count"] = len(requested_permissions)

    return record


def compute_pairwise_values(this_row, other_row):
    this_perms = this_row["_requested_permissions_set"]
    other_perms = other_row["_requested_permissions_set"]

    perms_added = sorted(this_perms - other_perms)
    perms_absent = sorted(other_perms - this_perms)

    this_row["perms_added"] = "; ".join(perms_added)
    this_row["perms_absent"] = "; ".join(perms_absent)

    this_row["pair_same_sha256"] = int(this_row["sha256"] == other_row["sha256"])
    this_row["pair_same_signer_cert"] = int(this_row["signer_cert_sha256"] == other_row["signer_cert_sha256"])
    this_row["pair_same_version"] = int(
        this_row["versionCode"] == other_row["versionCode"]
        and this_row["versionName"] == other_row["versionName"]
    )

    def diff_int(key):
        a = this_row.get(key)
        b = other_row.get(key)
        if a is None or b is None:
            return None
        return a - b

    this_row["pair_diff_size_bytes"] = diff_int("size_bytes")
    this_row["pair_diff_requested_permissions_count"] = diff_int("requested_permissions_count")
    this_row["pair_diff_declared_permissions_count"] = diff_int("declared_permissions_count")
    this_row["pair_diff_activities_all"] = diff_int("activities_all")
    this_row["pair_diff_activities_exported"] = diff_int("activities_exported")
    this_row["pair_diff_services_all"] = diff_int("services_all")
    this_row["pair_diff_services_exported"] = diff_int("services_exported")
    this_row["pair_diff_receivers_all"] = diff_int("receivers_all")
    this_row["pair_diff_receivers_exported"] = diff_int("receivers_exported")
    this_row["pair_diff_providers_all"] = diff_int("providers_all")
    this_row["pair_diff_providers_exported"] = diff_int("providers_exported")


def main():
    rows = []

    for package_dir in sorted(ROOT.iterdir()):
        if not package_dir.is_dir():
            continue

        play_row = load_store_record(package_dir, "play")
        rustore_row = load_store_record(package_dir, "rustore")

        if play_row and rustore_row:
            compute_pairwise_values(play_row, rustore_row)
            compute_pairwise_values(rustore_row, play_row)

        for row in [play_row, rustore_row]:
            if row:
                rows.append(row)

    fieldnames = [
        "package",
        "store",
        "apk_filename",
        "versionCode",
        "versionName",
        "sha256",
        "signer_cert_sha256",
        "size_bytes",
        "requested_permissions_count",
        "declared_permissions_count",
        "activities_all",
        "activities_exported",
        "services_all",
        "services_exported",
        "receivers_all",
        "receivers_exported",
        "providers_all",
        "providers_exported",
        "perms_added",
        "perms_absent",
        "pair_same_sha256",
        "pair_same_signer_cert",
        "pair_same_version",
        "pair_diff_size_bytes",
        "pair_diff_requested_permissions_count",
        "pair_diff_declared_permissions_count",
        "pair_diff_activities_all",
        "pair_diff_activities_exported",
        "pair_diff_services_all",
        "pair_diff_services_exported",
        "pair_diff_receivers_all",
        "pair_diff_receivers_exported",
        "pair_diff_providers_all",
        "pair_diff_providers_exported",
    ]

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            clean_row = {k: row.get(k) for k in fieldnames}
            writer.writerow(clean_row)

    print(f"Wrote: {OUT.resolve()}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()
