#!/usr/bin/env bash
set -euo pipefail

ROOT="dataset2"
SCRIPT="scripts/dataset2/extract_manifest_security_surface.py"

if [ ! -f "$SCRIPT" ]; then
  echo "ERROR: $SCRIPT not found"
  exit 1
fi

if [ ! -d "$ROOT" ]; then
  echo "ERROR: $ROOT not found"
  exit 1
fi

for pkg_dir in "$ROOT"/*; do
  [ -d "$pkg_dir" ] || continue

  for store in play rustore; do
    store_dir="$pkg_dir/$store"
    [ -d "$store_dir" ] || continue

    apk="$(find "$store_dir" -maxdepth 1 -type f -name "*.apk" | head -n 1)"

    if [ -z "${apk:-}" ]; then
      echo "[WARN] No APK in $store_dir"
      continue
    fi

    echo "[INFO] Processing: $apk"
    python3 "$SCRIPT" "$apk" "$store_dir"
    echo "[OK] Wrote results into: $store_dir"
    echo
  done
done

echo "[DONE] All packages processed."
