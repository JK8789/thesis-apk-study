# thesis-apk-study

This repository contains a small comparative dataset of Android APKs (RU vs EU apps) and scripts to extract features from:
- Local APK contents (AndroidManifest.xml via Androguard)
- VirusTotal metadata (previously collected and stored under `results/vt/`)

The goal is to build **pair-wise comparison tables** between matched RU/EU apps in multiple categories (permissions, components, exported components, etc.).

## Repository structure

- `data/`
  - `ru/` RU APKs
  - `eu/` EU APKs
  - `dicts`
    - `mvnrepo`
        - `ads`
        - `analytics`
        - `network`
        - `payments`
  - `meta/apps.csv` input table: list of apps contained region, category, pair_id, app_name,	apk_path,	sha256 columns

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
  - `datasafety`
  - `libs_longest`
  - `mvnrepo_dict`
  - `native`

VirusTotal reports were downloaded via vt-cli (VirusTotal API v3) and stored as results/vt/file/<sha256>.json. These raw JSON files are parsed by scripts/build_vt_csv.py into results/vt/vt_features.csv.

Local AndroidManifest analysis is done with Androguard. I parse each APK and extract permissions, SDK versions, debuggable flag, component counts, and exported component counts, using scripts/extract_manifest.py, saved as results/manifest/<sha256>.json, and then aggregated by scripts/build_local_csv.py into results/local/local_from_manifest.csv.

## PART 1 - Permissions 

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
  - `pair_id, permission, status` where status is `ru_only`, `eu_only`, `common`

### Metrics long format (for plots)
- `results/pairs/pairs_metrics_long.csv`  
  `category, pair_id, ru_app, eu_app, metric, value`  
  (handy for pair-wise plotting).

### Components tables (from VT lists)
- `results/pairs/pair_component_status_vt.csv`  
  Per pair per component name (using VT component name lists):
  - `category, pair_id, component_type, component_name, status`
  - status is `ru_only`, `eu_only`, `common`


## PART 2 Data Safety

In this part I analyze Google Play Data Safety disclosures for each app and compare RU and EU apps.

I collected Data Safety information from previously downloaded datasets and transformed it into structured tables that allow pair wise comparison.

The goal of this part is to understand:

- what types of data apps declare they collect
- purposes of data usage
- differences between RU and EU apps
- whether paired apps declare the same data practices

Output folder used in this part:
- results/datasafety/

---

### 1. Build Data Safety long table

Script:  
scripts/build_datasafety_long.py

What I did  
I converted raw Data Safety metadata into a long format table where each row represents one data type disclosure for one app.

Input  
Source dataset with parsed Data Safety metadata.

Output  
results/datasafety/datasafety_long.csv

Columns:
- sha256  
- region  
- category  
- pair_id  
- app_name  
- package  
- data_type. Example location contacts identifiers  
- collected. Whether the app declares collection  
- shared. Whether the app declares sharing  
- purpose. Purpose category such as analytics advertising app functionality  

This table is the base representation of declared data practices.

---

### 2. Build data type and purpose pairs

Script:  
scripts/build_datasafety_pairs_purpose.py

What I did  
I created a pair wise comparison table that shows differences between RU and EU apps for each data type and purpose.

Input  
results/datasafety/datasafety_long.csv

Output  
results/datasafety/datasafety_pairs_purpose.csv

Columns:
- pair_id  
- data_type  
- purpose  
- status. One of ru_only eu_only common  

This allows direct comparison of declared purposes between paired apps.

---

### 3. Aggregate Data Safety per app

Script:  
scripts/build_datasafety_summary.py

What I did  
I calculated summary metrics per app to quantify declared data collection.

Input  
results/datasafety/datasafety_long.csv

Output  
results/datasafety/datasafety_summary_per_app.csv

Columns:
- sha256  
- region  
- category  
- pair_id  
- app_name  
- package  
- data_types_count. Number of declared data types  
- purposes_count. Number of declared purposes  
- collected_types_count  
- shared_types_count  

This provides a per app footprint of declared data practices.

---

### 4. Pair wise Data Safety comparison

Script:  
scripts/build_datasafety_pairs_summary.py

What I did  
I compared RU and EU apps per pair to measure differences in declared data collection.

Input  
results/datasafety/datasafety_summary_per_app.csv

Output  
results/datasafety/datasafety_pairs_summary.csv

Columns:
- pair_id  
- ru_data_types_count  
- eu_data_types_count  
- delta_data_types_ru_minus_eu  
- ru_purposes_count  
- eu_purposes_count  
- delta_purposes_ru_minus_eu  

This table is the main quantitative comparison for Data Safety.

---

## Main outcome of Part 2

In this part I:

- transformed Data Safety disclosures into structured datasets  
- compared declared data collection between RU and EU apps  
- analyzed purposes of data usage  
- quantified differences in declared data practices per pair  
- created pair wise tables for visualization and statistical analysis


## PART 3 - Third-party libraries

This part analyzes third-party libraries used inside APKs and compares the RU and EU ecosystems.
It combines three complementary approaches:

1) **Library discovery from DEX namespaces (keywords + deep hits)**
   I extracted class/package namespaces from APKs and detected SDK-related prefixes using keyword patterns (e.g., `.ads.`, `payment`, `analytics`, `push`, etc.).
   This helps to identify region specific SDK namespaces that may not exist in curated datasets.

2) **Focused “important SDK” dictionary from Maven Repository tags**
   I build a dictionary of SDK candidates from mvnrepository tag pages (e.g., *payments*, *ads*, *analytics*, *network*), then keep only those prefixes that appear in my APK class inventories.
   This answers directly: “Do RU and EU apps rely on the same important SDK families?”

3) **Native library (.so) analysis**
   I extract embedded native libraries (`lib/<abi>/*.so`) from APKs and compare RU-only vs EU-only vs common native dependencies.

Output folders used in this part:
- `results/classes/`  extracted class namespaces per APK
- `results/prefixes/`  prefix inventories per APK
- `results/libs_longest/`  longest-prefix library matching + deep hits
- `results/libs_longest/analysis/`  type summaries and per-app lists
- `data/dicts/mvnrepo/`  Maven tag dictionaries and hits
- `results/native/`  native `.so` extraction and summaries

---

### 1. Extract class names from APKs

Script:  
scripts/extract_classes.py

What I did  
I extracted all DEX class names from each APK.

Input  
data/meta/apps.csv  
Columns:
- apk_path  
- sha256  

Output  
results/classes/<SHA256>.txt  

Format  
One class per line in dot notation, for example  
com.google.android.gms.ads.AdView

---

### 2. Build package prefix inventories

Script:  
scripts/extract_prefixes.py

What I did  
I converted class names into package prefixes.  
I used prefixes because they approximate library boundaries better than individual classes.

Input  
results/classes/<SHA256>.txt

Outputs  

1) results/prefixes/<SHA256>.txt  
Unique prefixes from depth 2 to 6.

2) results/prefixes/<SHA256>_counts.csv  

Columns:
- prefix. Package prefix. Example com.google.android.gms.ads  
- class_count. Number of classes using this prefix  
- depth. Number of segments in the prefix

3) results/prefixes/prefix_stats.csv  

Columns per app:
- classes_nonplatform. Number of non Android framework classes  
- unique_prefixes_total. Total unique prefixes  
- unique_prefixes_d2 d3 d4. Prefix counts by depth  
- first_party_guess_prefix. Heuristic guess of app main namespace  
- obfuscation_score. Heuristic signal of obfuscation  
- top_prefix and top_prefix_class_count. Most frequent prefix

I used this step to separate first party code from potential third party libraries.

---

### 3. Library matching with AndroLibZoo

Script:  
scripts/match_androlibzoo_longest.py

What I did  
I matched prefixes against a known library list using longest prefix matching.  
This improves detection when SDK namespaces are nested.

Inputs  
- prefix inventories  
- data/androlibzoo/AndroLibZoo.lst

Outputs  
results/libs_longest/

Main files:
- libs_per_app_long.csv  
- libs_match_stats.csv  
- libs_summary_region.csv  
- pairs_libs_diff.csv  

These describe which libraries appear per app and how RU and EU differ.

---

### 4. Detect deep keyword library signals

Script that produces this output  
scripts/match_androlibzoo_longest.py

What I did  
I searched prefix inventories for strong SDK keywords even if the library is not present in AndroLibZoo.

Input  
- results/prefixes/<SHA256>_counts.csv  
- keyword patterns defined in the script

Output  
results/libs_longest/keyword_deep_hits.csv

Columns:
- prefix. Detected namespace  
- depth. Prefix depth  
- class_count. Number of classes using it  
- sha256 region category pair_id app_name package

This step captures ecosystem specific SDK namespaces.

---

### 5. Label deep hits with library types

Script:  
scripts/label_keyword_deep_hits.py

What I did  
I assigned a functional type to each detected namespace.

Input  
results/libs_longest/keyword_deep_hits.csv

Output  
results/libs_longest/keyword_deep_hits_typed.csv

New column:
- type. One of ads analytics payments push crash networking anti_fraud other

---

### 6. Build automatic library taxonomy

Script:  
scripts/build_library_taxonomy.py

What I did  
I created a mapping from prefix to library type.

Inputs  
- matched libraries  
- keyword deep hits

Output  
data/meta/library_taxonomy_auto.csv

Columns:
- prefix  
- type_auto

This file acts as the classification layer.

---

### 7. Library type analysis per app

Script:  
scripts/analyze_library_types_with_lists.py

What I did  
I calculated how many libraries of each type appear in each app and stored the actual prefix lists.

Inputs  
- library taxonomy  
- keyword deep hits typed  
- matched libraries  
- apps_baseline.csv for ordering

Output folder  
results/libs_longest/analysis/

Main output  
library_types_per_app_with_lists.csv

Columns:
- counts per type ads analytics payments push crash networking anti_fraud other  
- lists per type such as ads_list payments_list  
- metadata sha256 region category pair_id app_name package

Additional outputs  

library_types_region_summary.csv  
Here:
- mean means average number of libraries of a given type per app  
- median means middle value which is more robust to outliers

library_types_pair_deltas.csv  
Shows RU minus EU differences per pair.

This is one of the main result layers.

---

### 8. Maven based important SDK dictionary

Scripts:
- scripts/mvn_parse_saved_pages.py  
- scripts/filter_candidates_by_classes_source.py  

What I did  
I created dictionaries of important SDK families using Maven tags and kept only those that appear in my APK dataset.

Inputs  
- saved HTML pages in data/mvn_pages/<tag>/  
- class inventories

Outputs per tag  
data/dicts/mvnrepo/<tag>/

Files:
- coords_ranked.csv  
- prefix_candidates.txt  
- prefix_hits.txt  
- hits_per_app.csv  
- hits_summary_region.csv  

These files support RU only EU only common comparisons for important SDK families.

---

### 9. Native library extraction

Script:  
scripts/extract_native_libs.py

What I did  
I extracted native shared libraries from APK files.

Input  
APK files

Output folder  
results/native/

Main file  
native_libs_per_app.csv

Columns:
- native_so_count_total. Total .so files  
- native_so_count_unique. Unique .so names  
- native_so_names. List of names  
- native_abis. ABI list  
- native_distinct_abis. Number of ABIs  
- native_top_abi. Most frequent ABI

---

### 10. Native ecosystem comparison

Script:  
scripts/native_venn_summary.py

What I did  
I compared unique native libraries between RU and EU.

Input  
results/native/native_libs_per_app.csv

Output  
results/native/native_summary.csv

Columns:
- ru_only_count eu_only_count common_count  
- ru_only_list eu_only_list common_list

---

## Main outcome of Part 3

In this part I:

- identified third party SDK usage inside APKs  
- compared RU and EU SDK ecosystems  
- classified libraries into functional categories  
- evaluated important SDK families using Maven tags  
- analyzed native dependency differences  
- identified region specific patterns in library usage
