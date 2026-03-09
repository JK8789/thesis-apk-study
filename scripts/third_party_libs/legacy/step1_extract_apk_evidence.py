#!/usr/bin/env python3
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import zipfile
import gc
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# -----------------------------
# CONFIG (hardcoded)
# -----------------------------
APPS_CSV = Path("data/meta/apps.csv")
OUT_DIR = Path("results/libs_phase2_step1")

TOP_N_PREFIXES_TO_STORE = 100
RESUME_SKIP_IF_EXISTS = True

TMP_DIR = Path("tmp/step1_dexdump")  # working directory for extracted dex

SKIP_PREFIXES = (
    "android.", "androidx.", "kotlin.", "kotlinx.", "java.", "javax.", "dalvik.",
    "org.jetbrains.", "org.intellij.",
)

USES_LIBRARY_RE = re.compile(r"<uses-library\b[^>]*\bandroid:name=\"([^\"]+)\"", re.IGNORECASE)
USES_NATIVE_LIBRARY_RE = re.compile(r"<uses-native-library\b[^>]*\bandroid:name=\"([^\"]+)\"", re.IGNORECASE)

CLASS_DESC_RE = re.compile(r"Class descriptor\s*:\s*'([^']+)'")


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def safe_slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    return s[:200] if len(s) > 200 else s


def depth_prefix(pkg: str, depth: int) -> str:
    parts = pkg.split(".")
    return pkg if len(parts) < depth else ".".join(parts[:depth])


def should_skip_prefix(p: str) -> bool:
    return any(p.startswith(s) for s in SKIP_PREFIXES)


def list_native_sos(apk_path: Path):
    out = []
    with zipfile.ZipFile(apk_path, "r") as z:
        for name in z.namelist():
            if name.startswith("lib/") and name.endswith(".so"):
                parts = name.split("/")
                abi = parts[1] if len(parts) >= 3 else ""
                out.append({"abi": abi, "path_in_apk": name, "so_name": parts[-1]})
    return out


def list_dex_entries(apk_path: Path):
    with zipfile.ZipFile(apk_path, "r") as z:
        dexes = []
        for n in z.namelist():
            base = os.path.basename(n)
            if re.fullmatch(r"classes\d*\.dex", base):
                dexes.append(n)
        return sorted(dexes)


def extract_dex_files(apk_path: Path, out_tmp: Path):
    """
    Extract all classes*.dex into out_tmp and return list of extracted paths.
    """
    extracted = []
    with zipfile.ZipFile(apk_path, "r") as z:
        for dex_name in list_dex_entries(apk_path):
            target = out_tmp / os.path.basename(dex_name)
            with z.open(dex_name) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(target)
    return extracted


def descriptor_to_dot(desc: str):
    # Lcom/example/Foo; -> com.example.Foo
    if not desc:
        return None
    if desc.startswith("L") and desc.endswith(";"):
        desc = desc[1:-1]
    return desc.replace("/", ".") if "/" in desc or "." in desc else None


def class_to_package(dot_class: str):
    if not dot_class or "." not in dot_class:
        return None
    return ".".join(dot_class.split(".")[:-1])


def run_dexdump_list_classes(dex_path: Path):
    """
    Uses dexdump to list class descriptors.
    Returns: set of dot-notation class names.
    """
    # -d prints details including "Class descriptor"
    proc = subprocess.run(
        ["dexdump", "-d", str(dex_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="ignore",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"dexdump failed for {dex_path.name}: {proc.stderr[:300]}")

    classes = set()
    for m in CLASS_DESC_RE.finditer(proc.stdout):
        desc = m.group(1)
        dot = descriptor_to_dot(desc)
        if dot:
            classes.add(dot)
    return classes


def parse_uses_from_manifest_text(manifest_text: str):
    uses_lib = sorted(set(USES_LIBRARY_RE.findall(manifest_text or "")))
    uses_native = sorted(set(USES_NATIVE_LIBRARY_RE.findall(manifest_text or "")))
    return uses_lib, uses_native


def try_apktool_manifest(apk_path: Path, tmp_apktool_dir: Path):
    """
    Optional: uses apktool to decode manifest to readable XML then parse uses-* tags.
    Returns (uses_library, uses_native_library, error_str_or_empty)
    """
    if shutil.which("apktool") is None:
        return [], [], "apktool not found (uses-* not parsed)"

    # Decode only manifest/resources fast-ish: apktool d -f -s
    # -s: no sources; -f: force overwrite
    try:
        if tmp_apktool_dir.exists():
            shutil.rmtree(tmp_apktool_dir)
        ensure_dir(tmp_apktool_dir.parent)

        proc = subprocess.run(
            ["apktool", "d", "-f", "-s", str(apk_path), "-o", str(tmp_apktool_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="ignore",
        )
        if proc.returncode != 0:
            return [], [], f"apktool decode failed: {proc.stderr[:300]}"

        manifest_path = tmp_apktool_dir / "AndroidManifest.xml"
        if not manifest_path.exists():
            return [], [], "apktool produced no AndroidManifest.xml"

        txt = manifest_path.read_text(encoding="utf-8", errors="ignore")
        uses_lib, uses_native = parse_uses_from_manifest_text(txt)
        return uses_lib, uses_native, ""
    except Exception as e:
        return [], [], f"apktool exception: {e}"


def read_apps_csv(csv_path: Path):
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"region", "category", "pair_id", "app_name", "apk_path", "sha256", "package"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"apps.csv missing required columns: {sorted(missing)}")
        return list(reader)


def main():
    # sanity: dexdump must exist
    if shutil.which("dexdump") is None:
        print("ERROR: 'dexdump' not found in PATH.")
        print("Install Android build-tools and ensure dexdump is in PATH (see instructions below).")
        raise SystemExit(1)

    repo_root = Path(".").resolve()
    out_root = repo_root / OUT_DIR

    per_app_dir = out_root / "per_app"
    classes_dir = out_root / "classes"
    agg_dir = out_root / "aggregate"
    logs_dir = out_root / "logs"

    ensure_dir(per_app_dir)
    ensure_dir(classes_dir)
    ensure_dir(agg_dir)
    ensure_dir(logs_dir)
    ensure_dir(repo_root / TMP_DIR)

    run_log = logs_dir / "run.log"

    rows = read_apps_csv(repo_root / APPS_CSV)

    summary_rows = []
    agg_d3 = {"eu": Counter(), "ru": Counter()}
    agg_d4 = {"eu": Counter(), "ru": Counter()}

    with run_log.open("a", encoding="utf-8") as log:
        log.write(f"\nRun started: {datetime.now(timezone.utc).isoformat(timespec="seconds")}Z\n")
        log.write(f"Total rows: {len(rows)}\n")
        log.flush()

        for idx, r in enumerate(rows, start=1):
            t0 = time.time()

            region = (r.get("region") or "").strip().lower()
            category = (r.get("category") or "").strip()
            pair_id = (r.get("pair_id") or "").strip()
            app_name = (r.get("app_name") or "").strip()
            apk_path_rel = (r.get("apk_path") or "").strip()
            sha_csv = (r.get("sha256") or "").strip().lower()
            pkg_csv = (r.get("package") or "").strip()

            apk_path = (repo_root / apk_path_rel).resolve()
            rec_id = safe_slug(f"{region}__{pkg_csv or app_name}__{sha_csv[:12] or idx}")

            per_app_json = per_app_dir / f"{rec_id}.json"
            classes_txt = classes_dir / f"{rec_id}__classes.txt"
            packages_txt = classes_dir / f"{rec_id}__packages.txt"

            if RESUME_SKIP_IF_EXISTS and per_app_json.exists() and classes_txt.exists() and packages_txt.exists():
                msg = f"[{idx}/{len(rows)}] {rec_id} SKIP"
                print(msg)
                log.write(msg + "\n")
                log.flush()
                continue

            evidence = {
                "id": rec_id,
                "region": region,
                "category": category,
                "pair_id": pair_id,
                "app_name": app_name,
                "apk_path_csv": apk_path_rel,
                "apk_path": str(apk_path),
                "sha256_csv": sha_csv,
                "package_csv": pkg_csv,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "errors": [],
            }

            if not apk_path.exists():
                evidence["errors"].append(f"APK not found: {apk_path}")
                per_app_json.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
                msg = f"[{idx}/{len(rows)}] {rec_id} MISSING"
                print(msg)
                log.write(msg + "\n")
                log.flush()
                continue

            # hash + size
            try:
                sha_file = sha256_file(apk_path)
                evidence["sha256_file"] = sha_file
                evidence["sha256_match"] = (sha_csv == sha_file) if sha_csv else None
                evidence["apk_size_bytes"] = apk_path.stat().st_size
            except Exception as e:
                evidence["errors"].append(f"sha256/size error: {e}")

            # zip evidence: dex entries + native
            try:
                dex_entries = list_dex_entries(apk_path)
                evidence["dex_files"] = dex_entries
            except Exception as e:
                evidence["errors"].append(f"dex list error: {e}")
                evidence["dex_files"] = []

            try:
                native_sos = list_native_sos(apk_path)
                evidence["native_sos"] = native_sos
            except Exception as e:
                evidence["errors"].append(f"native so list error: {e}")
                evidence["native_sos"] = []

            # manifest uses-* (optional, via apktool)
            uses_lib, uses_native, apktool_err = try_apktool_manifest(
                apk_path, repo_root / TMP_DIR / f"apktool_{rec_id}"
            )
            evidence["uses_library"] = uses_lib
            evidence["uses_native_library"] = uses_native
            if apktool_err:
                evidence["errors"].append(apktool_err)

            # Extract classes from dex using dexdump (NO XREF, low memory)
            try:
                work_dir = repo_root / TMP_DIR / rec_id
                if work_dir.exists():
                    shutil.rmtree(work_dir)
                ensure_dir(work_dir)

                dex_paths = extract_dex_files(apk_path, work_dir)
                all_classes = set()
                for dp in dex_paths:
                    all_classes |= run_dexdump_list_classes(dp)

                all_classes_sorted = sorted(all_classes)
                all_packages_sorted = sorted({class_to_package(c) for c in all_classes_sorted if class_to_package(c)})

                classes_txt.write_text("\n".join(all_classes_sorted) + "\n", encoding="utf-8")
                packages_txt.write_text("\n".join(all_packages_sorted) + "\n", encoding="utf-8")

                evidence["classes_file"] = str(classes_txt)
                evidence["packages_file"] = str(packages_txt)
                evidence["dex_class_count"] = len(all_classes_sorted)
                evidence["dex_unique_packages"] = len(all_packages_sorted)

                # prefix counts
                d3 = Counter()
                d4 = Counter()
                for pkg in all_packages_sorted:
                    if should_skip_prefix(pkg):
                        continue
                    d3[depth_prefix(pkg, 3)] += 1
                    d4[depth_prefix(pkg, 4)] += 1

                evidence["top_prefixes_d3"] = [{"prefix": p, "count": c} for p, c in d3.most_common(TOP_N_PREFIXES_TO_STORE)]
                evidence["top_prefixes_d4"] = [{"prefix": p, "count": c} for p, c in d4.most_common(TOP_N_PREFIXES_TO_STORE)]

                if region in ("eu", "ru"):
                    agg_d3[region].update(d3)
                    agg_d4[region].update(d4)

            except Exception as e:
                evidence["errors"].append(f"dexdump extraction error: {e}")

            # write per-app json
            per_app_json.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

            # summary row
            so_names = sorted({x.get("so_name", "") for x in evidence.get("native_sos", []) if x.get("so_name")})
            top10_d3 = ";".join([f"{x['prefix']}:{x['count']}" for x in evidence.get("top_prefixes_d3", [])[:10]])
            top10_d4 = ";".join([f"{x['prefix']}:{x['count']}" for x in evidence.get("top_prefixes_d4", [])[:10]])

            elapsed = time.time() - t0
            summary_rows.append({
                "id": rec_id,
                "region": region,
                "category": category,
                "pair_id": pair_id,
                "app_name": app_name,
                "package_csv": pkg_csv,
                "apk_path_csv": apk_path_rel,
                "sha256_csv": sha_csv,
                "sha256_file": evidence.get("sha256_file", ""),
                "sha256_match": evidence.get("sha256_match", ""),
                "apk_size_bytes": evidence.get("apk_size_bytes", ""),
                "dex_files": "|".join(evidence.get("dex_files", [])),
                "dex_class_count": evidence.get("dex_class_count", ""),
                "dex_unique_packages": evidence.get("dex_unique_packages", ""),
                "native_so_count": len(evidence.get("native_sos", [])),
                "native_so_names": "|".join(so_names),
                "uses_library": ";".join(evidence.get("uses_library", [])),
                "uses_native_library": ";".join(evidence.get("uses_native_library", [])),
                "top_prefixes_d3": top10_d3,
                "top_prefixes_d4": top10_d4,
                "classes_file": str(classes_txt) if classes_txt.exists() else "",
                "packages_file": str(packages_txt) if packages_txt.exists() else "",
                "elapsed_seconds": round(elapsed, 3),
                "errors": " | ".join(evidence.get("errors", [])),
                "per_app_json": str(per_app_json),
            })

            msg = f"[{idx}/{len(rows)}] {rec_id} OK ({elapsed:.1f}s)"
            print(msg)
            log.write(msg + "\n")
            log.flush()

            gc.collect()

    # write summary csv
    summary_csv = out_root / "evidence_summary.csv"
    if summary_rows:
        with summary_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            w.writeheader()
            for row in summary_rows:
                w.writerow(row)

    # write aggregate prefix counts
    def write_agg(region: str, depth: int, counter: Counter):
        out = agg_dir / f"prefix_counts_{region}_d{depth}.csv"
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["prefix", "count"])
            for p, cnt in counter.most_common():
                w.writerow([p, cnt])

    for reg in ("eu", "ru"):
        write_agg(reg, 3, agg_d3[reg])
        write_agg(reg, 4, agg_d4[reg])

    print(f"\nDone. Output folder: {OUT_DIR}")


if __name__ == "__main__":
    main()

