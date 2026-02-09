# thesis-apk-study

This repository contains a small comparative dataset of Android APKs (RU vs EU apps) and scripts to extract features from:
- Local APK contents (AndroidManifest.xml via Androguard)
- VirusTotal metadata (previously collected and stored under `results/vt/`)

The goal is to build **pair-wise comparison tables** between matched RU/EU apps in multiple categories (permissions, components, exported components, etc.).

## Repository structure

- `data/`
  - `ru/` RU APKs
  - `eu/` EU APKs
  - `meta/` pairing metadata / input tables
- `scripts/` analysis scripts (manifest extraction, CSV building, QC, pair tables)
- `results/`
  - `manifest/` per-APK JSON extracted locally from AndroidManifest.xml
  - `local/` local feature tables derived from `results/manifest/`
  - `vt/`
    - `file/` raw VT file JSON responses
    - `vt_features.csv` parsed VT feature table
  - `baseline/` merged baseline CSV (local + VT features)
  - `qc/` quality-control reports
  - `pairs/` pair-wise comparison tables

VirusTotal reports were downloaded via vt-cli (VirusTotal API v3) and stored as results/vt/file/<sha256>.json. These raw JSON files are parsed by scripts/build_vt_csv.py into results/vt/vt_features.csv.
Local AndroidManifest analysis is done with Androguard. I parse each APK and extract permissions, SDK versions, debuggable flag, component counts, and exported component counts, using scripts/extract_manifest.py, saved as results/manifest/<sha256>.json, and then aggregated by scripts/build_local_csv.py into results/local/local_from_manifest.csv.

All pair-wise outputs are in `results/pairs/`:

### Pair summary table (per pair)
- `results/pairs/pairs_summary.csv`  
  One row per pair (RU app vs EU app). Contains:
  - RU/EU names, sha256, packages
  - permissions counts and delta:
    - `ru_perm_count_local`, `eu_perm_count_local`, `delta_perm_local_ru_minus_eu`
  - exported component totals and delta:
    - `ru_exported_comp_total`, `eu_exported_comp_total`, `delta_exported_total_ru_minus_eu`
  - VT scanned stats and VT permission counts

### Permissions tables
- `results/pairs/app_permissions_list.csv`  
  Local permissions in long format: one row per `(sha256, permission)`.

- `results/pairs/pairs_permissions_diff.csv`  
  Per pair:
  - counts: `perm_in_ru_only_count`, `perm_in_eu_only_count`, `common_perm_count`
  - lists: `ru_only_permissions`, `eu_only_permissions`, `common_permissions`

- `results/pairs/pair_permission_status.csv`  
  Per pair per permission:
  - `pair_id, permission, status` where status ∈ `ru_only`, `eu_only`, `common`

### Metrics long format (for plots)
- `results/pairs/pairs_metrics_long.csv`  
  `category, pair_id, ru_app, eu_app, metric, value`  
  (handy for pair-wise plotting).

### Components tables (from VT lists)
- `results/pairs/pair_component_status_vt.csv`  
  Per pair per component name (using VT component name lists):
  - `category, pair_id, component_type, component_name, status`
  - status ∈ `ru_only`, `eu_only`, `common`
