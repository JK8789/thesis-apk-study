#!/usr/bin/env python3
"""
Mirrored (back-to-back) barplots for third-party library differences (paired RU vs EU apps).

Visual:
  - RU bars on the LEFT (blue)
  - EU bars on the RIGHT (orange)
  - Axis tick labels displayed as positive counts on both sides

Inputs (relative to thesis-apk-study):
  1) data/dicts/mvnrepo/summary.csv
     columns include:
       pair_id, region, app_name, total_hit_count,
       ads_hit_count, analytics_hit_count, payments_hit_count, network_hit_count

  2) results/native/native_libs_per_app.csv
     columns include:
       pair_id, region, app_name, native_so_count_unique

Outputs (plots only):
  Plots/thirdparty_pairs/mirrored_mvn_total_hit_count.png/.svg
  Plots/thirdparty_pairs/mirrored_mvn_<tag>_hit_count.png/.svg   for tags ads/payments/analytics/network
  Plots/thirdparty_pairs/mirrored_native_unique_so_count.png/.svg

Run from thesis-apk-study/:
  python3 scripts/create_plots/create_thirdparty_mirrored_pairs.py
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


RU_COLOR = "tab:blue"      # RU left
EU_COLOR = "tab:orange"    # EU right

TAGS = ["ads", "payments", "analytics", "network"]


def _require_cols(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"{name}: missing columns {sorted(missing)}; found {list(df.columns)}")


def _build_pair_rows_keep_order(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """
    Build one row per pair_id (keep pair_id order as first appearance in df):
      label = 'RU app_name vs EU app_name'
      ru_val, eu_val from value_col
    """
    d = df.copy()
    d["region"] = d["region"].astype(str).str.strip().str.lower()

    pair_order = pd.unique(d["pair_id"])
    rows = []

    for pid in pair_order:
        g = d[d["pair_id"] == pid]
        g_ru = g[g["region"].eq("ru")]
        g_eu = g[g["region"].eq("eu")]
        if g_ru.empty or g_eu.empty:
            continue

        ru = g_ru.iloc[0]
        eu = g_eu.iloc[0]

        label = f"{str(ru['app_name'])} vs {str(eu['app_name'])}"
        ru_val = int(ru[value_col])
        eu_val = int(eu[value_col])

        rows.append((pid, label, ru_val, eu_val))

    out = pd.DataFrame(rows, columns=["pair_id", "label", "ru_val", "eu_val"])
    if out.empty:
        raise SystemExit(f"No valid RU/EU pairs found for value_col='{value_col}'.")
    return out


def mirrored_barplot_pairs(
    plot_df: pd.DataFrame,
    title: str,
    sentence: str,
    xlabel: str,
    out_png: Path,
    out_svg: Path,
) -> None:
    """
    RU drawn left using negative coords; EU drawn right using positive coords.
    Axis tick labels are shown as absolute counts.
    """
    y = list(range(len(plot_df)))
    ru_vals = (-plot_df["ru_val"]).tolist()  # draw left
    eu_vals = (plot_df["eu_val"]).tolist()   # draw right

    max_abs = float(max(plot_df["ru_val"].max(), plot_df["eu_val"].max()))
    xlim = max_abs * 1.15 + 0.5

    fig = plt.figure(figsize=(12, max(6, len(plot_df) * 0.32)), dpi=200)
    fig.subplots_adjust(top=0.86, right=0.82)

    fig.suptitle(title, fontsize=16, y=0.97)
    fig.text(0.5, 0.91, sentence, ha="center", va="top", fontsize=10)

    ax = fig.add_subplot(111)

    ax.barh(y, ru_vals, color=RU_COLOR, label="RU")
    ax.barh(y, eu_vals, color=EU_COLOR, label="EU")
    ax.axvline(0, linewidth=1.2, alpha=0.85)

    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["label"].tolist())

    ax.set_xlim(-xlim, xlim)
    ax.set_xlabel(xlabel)

    # show positive tick labels on both sides
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{int(abs(v))}"))

    ax.grid(axis="x", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)

    # legend outside
    ax.legend(
        frameon=False,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
    )

    # numeric labels at ends
    for yi, (ru, eu) in enumerate(zip(plot_df["ru_val"].tolist(), plot_df["eu_val"].tolist())):
        if ru > 0:
            ax.text(-ru - 0.2, yi, str(int(ru)), va="center", ha="right", fontsize=8, color=RU_COLOR)
        if eu > 0:
            ax.text(eu + 0.2, yi, str(int(eu)), va="center", ha="left", fontsize=8, color=EU_COLOR)

    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    mvn_summary_path = Path("data/dicts/mvnrepo/summary.csv")
    native_path = Path("results/native/native_libs_per_app.csv")

    out_dir = Path("Plots/thirdparty_pairs")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not mvn_summary_path.exists():
        raise SystemExit(f"Missing mvn summary input: {mvn_summary_path}")
    if not native_path.exists():
        raise SystemExit(f"Missing native input: {native_path}")

    # -------------------------
    # Maven summary (TOTAL + per-tag) from one file
    # -------------------------
    mvn = pd.read_csv(mvn_summary_path)
    _require_cols(mvn, {"pair_id", "region", "app_name", "total_hit_count"}, name=str(mvn_summary_path))

    # numeric conversion
    mvn["total_hit_count"] = pd.to_numeric(mvn["total_hit_count"], errors="coerce").fillna(0).astype(int)

    # 1) TOTAL Maven hits plot
    total_pairs = _build_pair_rows_keep_order(mvn, value_col="total_hit_count")
    mirrored_barplot_pairs(
        plot_df=total_pairs,
        title="Third-party libraries (paired): total Maven SDK hits",
        sentence="Each row is a matched RU–EU app pair. Bars show the total number of detected Maven SDK hits per app (RU left, EU right).",
        xlabel="Total Maven SDK hit count (per app)",
        out_png=out_dir / "mirrored_mvn_total_hit_count.png",
        out_svg=out_dir / "mirrored_mvn_total_hit_count.svg",
    )

    # 2) Per-tag Maven hits plots (ads/payments/analytics/network)
    for tag in TAGS:
        col = f"{tag}_hit_count"
        if col not in mvn.columns:
            # skip silently if not present
            continue
        mvn[col] = pd.to_numeric(mvn[col], errors="coerce").fillna(0).astype(int)

        tag_pairs = _build_pair_rows_keep_order(mvn, value_col=col)
        mirrored_barplot_pairs(
            plot_df=tag_pairs,
            title=f"Third-party libraries (paired): Maven SDK hits ({tag})",
            sentence=f"Each row is a matched RU–EU app pair. Bars show the number of detected Maven SDK hits for the '{tag}' tag (RU left, EU right).",
            xlabel=f"Maven SDK hit count ({tag})",
            out_png=out_dir / f"mirrored_mvn_{tag}_hit_count.png",
            out_svg=out_dir / f"mirrored_mvn_{tag}_hit_count.svg",
        )

    # -------------------------
    # Native libs per app
    # -------------------------
    nat = pd.read_csv(native_path)
    _require_cols(nat, {"pair_id", "region", "app_name", "native_so_count_unique"}, name=str(native_path))
    nat["native_so_count_unique"] = pd.to_numeric(nat["native_so_count_unique"], errors="coerce").fillna(0).astype(int)

    native_pairs = _build_pair_rows_keep_order(nat, value_col="native_so_count_unique")
    mirrored_barplot_pairs(
        plot_df=native_pairs,
        title="Third-party libraries (paired): unique native libraries (.so)",
        sentence="Each row is a matched RU–EU app pair. Bars show the number of unique native .so libraries per app (RU left, EU right).",
        xlabel="Unique native .so libraries (per app)",
        out_png=out_dir / "mirrored_native_unique_so_count.png",
        out_svg=out_dir / "mirrored_native_unique_so_count.svg",
    )

    print("Saved plots to:", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
