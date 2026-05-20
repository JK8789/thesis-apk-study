# Thesis plot scripts with project-relative paths

Assumed project layout:
- thesis-apk-study/                        -> project root
- thesis-apk-study/scripts/thesis_plot_scripts_real/ -> scripts folder
- thesis-apk-study/Plots/thesis_plot_scripts_real/   -> output figures/tables

Each script auto-detects the root with:
`Path(__file__).resolve().parents[2]`

Main data files used:
- `results/local/local_from_manifest.csv`
- `results/local/extracted_local_manifest_features and lists.csv`
- `results/native/native_summary.csv`
- `results/native/native_libs_per_app.csv`
- `results/libs_longest/libs_summary_region.csv`
- `results/datasafety/datasafety_long.csv`
- `dataset2/dataset2.csv`
- `data/dicts/mvnrepo/mvn_repo_summary.csv`
- `data/dicts/mvnrepo/ads/hits_summary_region_ads.csv`
- `data/dicts/mvnrepo/analytics/hits_summary_region_analytics.csv`
- `data/dicts/mvnrepo/network/hits_summary_region_network.csv`
- `data/dicts/mvnrepo/payments/hits_summary_region_pyaments.csv`

Run example:
```bash
cd thesis-apk-study/scripts/thesis_plot_scripts_real
python3 01_fig6_1_total_permissions_dumbbell.py
```
