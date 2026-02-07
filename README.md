# thesis-apk-study

This repository contains a small comparative dataset of Android APKs (RU vs EU apps) and scripts to extract features from:
- Local APK contents (AndroidManifest.xml via Androguard)
- VirusTotal metadata (previously collected and stored under `results/vt/`)

The goal is to build **pair-wise comparison tables** between matched RU/EU apps in multiple categories (permissions, components, exported components, etc.).

## Repository structure

- `data/`
  - `ru/` RU APKs
  - `eu/` EU APKs
  - `meta/` pairing metadata / input tables (if present)
- `scripts/` analysis scripts (manifest extraction, CSV building, QC, pair tables)
- `results/`
  - `manifest/` per-APK JSON extracted locally from AndroidManifest.xml
  - `local/` local feature tables derived from `results/manifest/`
  - `vt/`
    - `file/` raw VT file JSON responses (if included)
    - `vt_features.csv` parsed VT feature table
  - `baseline/` merged baseline CSV (local + VT features)
  - `qc/` quality-control reports
  - `pairs/` pair-wise comparison tables
