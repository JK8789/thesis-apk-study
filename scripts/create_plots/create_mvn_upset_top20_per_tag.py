#!/usr/bin/env python3
"""
Create UpSet plots (bars + RU/EU matrix) for top Maven SDK libs per tag.

Reads:
  data/dicts/mvnrepo/<tag>/hits_per_app.csv
for tags: ads, payments, analytics, network

Writes (plots only):
  Plots/mvn_upset/<tag>_upset_top20.png
  Plots/mvn_upset/<tag>_upset_top20.svg

Run from thesis-apk-study/:
  python3 scripts/create_plots/create_mvn_upset_top20_per_tag.py
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import matplotlib.pyplot as plt


TAGS = ["ads", "payments", "analytics", "network"]
TOP_N = 20

EXPLANATION = (
    "Bars indicate how many applications include each Maven SDK library in the RU and EU datasets "
    "(20 apps per region); stacked colors represent region-specific counts."
)


# --------------------------
# Parsing helpers
# --------------------------

def _normalize_region(val: Any) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().lower()
    if s in {"ru", "russia"}:
        return "ru"
    if s in {"eu", "europe"}:
        return "eu"
    return None


def _find_region_col(df: pd.DataFrame) -> str | None:
    # common names first
    for c in df.columns:
        if c.strip().lower() in {"region", "store_region", "market", "geo"}:
            return c
    # fallback: first column that contains mostly ru/eu values
    for c in df.columns:
        vals = df[c].dropna().astype(str).str.lower().str.strip()
        if len(vals) and vals.isin(["ru", "eu"]).mean() > 0.5:
            return c
    return None


def _try_parse_json_like(s: str) -> Any:
    try:
        return json.loads(s)
    except Exception:
        pass
    try:
        return ast.literal_eval(s)
    except Exception:
        return None


def parse_libs_cell(cell: Any) -> set[str]:
    """
    Parse a cell representing Maven libs/hits/prefixes for one app row.
    Supported formats (best effort):
      - JSON dict: {"com.foo": 2, "com.bar": 1} -> keys are libs
      - JSON list: ["com.foo", "com.bar"]
      - Python literal dict/list (single quotes)
      - Delimited string: "com.foo;com.bar" or "com.foo, com.bar"
      - Single string lib
    """
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return set()

    s = str(cell).strip()
    if not s or s.lower() == "nan":
        return set()

    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        parsed = _try_parse_json_like(s)
        if isinstance(parsed, dict):
            return {str(k).strip() for k in parsed.keys() if str(k).strip()}
        if isinstance(parsed, list):
            return {str(x).strip() for x in parsed if str(x).strip()}

    if ";" in s:
        parts = [p.strip() for p in s.split(";")]
        return {p for p in parts if p}
    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        return {p for p in parts if p}

    return {s}


def _find_libs_col(df: pd.DataFrame, region_col: str) -> str | None:
    preferred = [
        "libs", "libraries", "prefixes", "mvn_prefixes", "sdk_prefixes",
        "hits", "hits_prefixes", "matches", "found_prefixes",
    ]
    lower_map = {c.lower(): c for c in df.columns}
    for p in preferred:
        if p in lower_map and lower_map[p] != region_col:
            return lower_map[p]

    candidates = [c for c in df.columns if c != region_col]
    if not candidates:
        return None

    best_col = None
    best_score = -1.0
    for c in candidates:
        ser = df[c].dropna().astype(str)
        if ser.empty:
            continue
        score = (
            ser.str.contains(r"[;\[,]").mean()
            + ser.str.contains(r"^\s*[\{\[]").mean()
        )
        if score > best_score:
            best_score = score
            best_col = c

    return best_col


# --------------------------
# Build stats per tag
# --------------------------

def build_counts_for_tag(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    region_col = _find_region_col(df)
    if region_col is None:
        raise ValueError(f"Could not find region column in {csv_path}. Columns: {list(df.columns)}")

    libs_col = _find_libs_col(df, region_col=region_col)
    if libs_col is None:
        raise ValueError(f"Could not find libs/hits column in {csv_path}. Columns: {list(df.columns)}")

    df["_region_norm"] = df[region_col].apply(_normalize_region)
    df = df[df["_region_norm"].isin(["ru", "eu"])].copy()
    df["_libs_set"] = df[libs_col].apply(parse_libs_cell)

    ru_apps_by_lib: dict[str, set[int]] = {}
    eu_apps_by_lib: dict[str, set[int]] = {}

    for idx, row in df.iterrows():
        region = row["_region_norm"]
        libs = row["_libs_set"]
        if not libs:
            continue
        target = ru_apps_by_lib if region == "ru" else eu_apps_by_lib
        for lib in libs:
            target.setdefault(lib, set()).add(idx)

    all_libs = sorted(set(ru_apps_by_lib) | set(eu_apps_by_lib))

    stats = []
    for lib in all_libs:
        ru = len(ru_apps_by_lib.get(lib, set()))
        eu = len(eu_apps_by_lib.get(lib, set()))
        total = ru + eu
        stats.append((lib, ru, eu, total))

    out = pd.DataFrame(stats, columns=["lib", "ru_apps", "eu_apps", "total_apps"])
    out = out.sort_values(["total_apps", "lib"], ascending=[False, True]).reset_index(drop=True)
    return out


# --------------------------
# Plot
# --------------------------

def plot_upset_like(
    tag: str,
    libs: list[str],
    ru_counts: list[int],
    eu_counts: list[int],
    out_png: Path,
    out_svg: Path,
) -> None:
    x = list(range(len(libs)))
    totals = [r + e for r, e in zip(ru_counts, eu_counts)]

    fig = plt.figure(figsize=(max(12, len(libs) * 0.7), 6), dpi=200)

    # Leave room at the top for title + explanatory sentence
    # (top=0.86 means plotting area ends at 86% of height)
    fig.subplots_adjust(top=0.86)

    gs = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[3.5, 1.2], hspace=0.05)
    ax_bar = fig.add_subplot(gs[0, 0])
    ax_mat = fig.add_subplot(gs[1, 0], sharex=ax_bar)

    # Title + explanatory sentence (right under the title)
    fig.suptitle(f"Top {TOP_N} Maven SDK libs: {tag} (RU vs EU)", fontsize=16, y=0.97)
    fig.text(0.5, 0.92, EXPLANATION, ha="center", va="top", fontsize=10)

    # Stacked bars
    ru_color = "tab:blue"
    eu_color = "tab:orange"

    ax_bar.bar(x, ru_counts, color=ru_color, label="RU")
    ax_bar.bar(x, eu_counts, bottom=ru_counts, color=eu_color, label="EU")

    ax_bar.set_ylabel("Apps containing lib")
    ax_bar.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.6)
    ax_bar.set_axisbelow(True)
    ax_bar.legend(loc="upper right", frameon=False)

    # Labels ABOVE bar:
    # EU (orange) on left half, RU (blue) on right half
    ymax = max(totals) if totals else 0
    pad = max(0.6, ymax * 0.02)

    for i, (r, e) in enumerate(zip(ru_counts, eu_counts)):
        if r == 0 and e == 0:
            continue
        y_text = (r + e) + pad
        x_left = i - 0.20
        x_right = i + 0.20

        if e > 0:
            ax_bar.text(x_left, y_text, str(e),
                        ha="center", va="bottom", fontsize=9, color=eu_color)
        if r > 0:
            ax_bar.text(x_right, y_text, str(r),
                        ha="center", va="bottom", fontsize=9, color=ru_color)

    # Matrix (RU/EU presence)
    ru_present = [r > 0 for r in ru_counts]
    eu_present = [e > 0 for e in eu_counts]

    y_ru, y_eu = 1, 0
    ax_mat.set_yticks([y_ru, y_eu])
    ax_mat.set_yticklabels(["RU", "EU"])
    ax_mat.hlines([y_ru, y_eu], xmin=-0.5, xmax=len(libs) - 0.5, linewidth=0.8, alpha=0.4)

    ru_x = [i for i, p in enumerate(ru_present) if p]
    eu_x = [i for i, p in enumerate(eu_present) if p]
    ax_mat.scatter(ru_x, [y_ru] * len(ru_x), s=60, color=ru_color)
    ax_mat.scatter(eu_x, [y_eu] * len(eu_x), s=60, color=eu_color)

    both_x = [i for i, (rp, ep) in enumerate(zip(ru_present, eu_present)) if rp and ep]
    for i in both_x:
        ax_mat.vlines(i, y_eu, y_ru, linewidth=1.0, alpha=0.6)

    ax_mat.set_xticks(x)
    ax_mat.set_xticklabels(libs, rotation=60, ha="right")
    ax_mat.set_xlabel("Libraries (Maven prefixes)")
    ax_mat.set_ylim(-0.7, 1.7)
    ax_mat.grid(False)

    for spine in ["top", "right"]:
        ax_mat.spines[spine].set_visible(False)
        ax_bar.spines[spine].set_visible(False)

    plt.setp(ax_bar.get_xticklabels(), visible=False)

    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)


# --------------------------
# Main
# --------------------------

def main() -> int:
    out_dir = Path("Plots/mvn_upset")
    out_dir.mkdir(parents=True, exist_ok=True)

    any_done = False

    for tag in TAGS:
        csv_path = Path(f"data/dicts/mvnrepo/{tag}/hits_per_app.csv")
        if not csv_path.exists():
            print(f"[WARN] Missing file for tag '{tag}': {csv_path}", file=sys.stderr)
            continue

        try:
            stats_df = build_counts_for_tag(csv_path)
        except Exception as e:
            print(f"[ERROR] {tag}: {e}", file=sys.stderr)
            continue

        if stats_df.empty:
            print(f"[WARN] No libs to plot for tag '{tag}'.", file=sys.stderr)
            continue

        plot_df = stats_df.head(TOP_N).copy()
        libs = plot_df["lib"].astype(str).tolist()
        ru_counts = plot_df["ru_apps"].astype(int).tolist()
        eu_counts = plot_df["eu_apps"].astype(int).tolist()

        out_png = out_dir / f"{tag}_upset_top{TOP_N}.png"
        out_svg = out_dir / f"{tag}_upset_top{TOP_N}.svg"

        plot_upset_like(
            tag=tag,
            libs=libs,
            ru_counts=ru_counts,
            eu_counts=eu_counts,
            out_png=out_png,
            out_svg=out_svg,
        )

        any_done = True
        print(f"Saved: {out_png}")
        print(f"Saved: {out_svg}")

    if not any_done:
        print("No plots were generated (missing inputs or parse errors).", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
