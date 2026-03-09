#!/usr/bin/env python3
"""
Mirrored (back-to-back) barplots for paired RU vs EU comparisons using raw counts.

Visual goal:
  - RU (blue) bars on the LEFT, displayed as positive counts
  - EU (orange) bars on the RIGHT, displayed as positive counts

Implementation detail:
  - RU is drawn with negative x-values so bars extend left,
    but x-axis tick labels are formatted as absolute values.

Input:
  results/pairs/pairs_summary.csv

Output (plots only):
  Plots/permissions_pairs/mirrored_perm_local.png/.svg
  Plots/permissions_pairs/mirrored_vt_dangerous_perm.png/.svg
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


TITLE_1 = "Paired comparison (mirrored): requested permissions per pair (RU vs EU)"
EXPL_1 = (
    "Each row is a matched RU–EU app pair. RU counts are shown on the left (blue) and EU counts on the right (orange); "
    "axis labels display positive counts on both sides."
)

TITLE_2 = "Paired comparison (mirrored): dangerous permissions per pair (RU vs EU)"
EXPL_2 = (
    "Each row is a matched RU–EU app pair. RU counts are shown on the left (blue) and EU counts on the right (orange); "
    "axis labels display positive counts on both sides."
)

RU_COLOR = "tab:blue"
EU_COLOR = "tab:orange"


def mirrored_barplot(
    df: pd.DataFrame,
    ru_col: str,
    eu_col: str,
    title: str,
    explanation: str,
    out_png: Path,
    out_svg: Path,
    xlabel: str,
) -> None:
    d = df.copy()

    d[ru_col] = pd.to_numeric(d[ru_col], errors="coerce")
    d[eu_col] = pd.to_numeric(d[eu_col], errors="coerce")
    d = d.dropna(subset=[ru_col, eu_col]).reset_index(drop=True)

    # y labels must be "ru_app vs eu_app"
    if {"ru_app", "eu_app"}.issubset(d.columns):
        d["_label"] = d["ru_app"].astype(str) + " vs " + d["eu_app"].astype(str)
    else:
        # fallback
        d["_label"] = d.get("pair_id", pd.Series([f"pair_{i+1}" for i in range(len(d))])).astype(str)

    # Keep your existing order unless you want sorting:
    # d = d.sort_values("_total", ascending=True).reset_index(drop=True)

    # Mirror: RU left, EU right
    ru_vals = (-d[ru_col]).tolist()  # negative for left extension
    eu_vals = (d[eu_col]).tolist()   # positive for right extension

    labels = d["_label"].tolist()
    y = list(range(len(d)))

    max_abs = float(max(d[ru_col].max(), d[eu_col].max()))
    xlim = max_abs * 1.15 + 0.5

    fig = plt.figure(figsize=(12, max(6, len(d) * 0.28)), dpi=200)
    fig.subplots_adjust(top=0.86, right=0.82)

    fig.suptitle(title, fontsize=16, y=0.97)
    fig.text(0.5, 0.91, explanation, ha="center", va="top", fontsize=10)

    ax = fig.add_subplot(111)

    ax.barh(y, ru_vals, color=RU_COLOR, label="RU")
    ax.barh(y, eu_vals, color=EU_COLOR, label="EU")

    ax.axvline(0, linewidth=1.2, alpha=0.85)

    ax.set_yticks(y)
    ax.set_yticklabels(labels)

    ax.set_xlim(-xlim, xlim)

    # ✅ Show ONLY positive counts on both sides
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{int(abs(v))}"))

    ax.set_xlabel(xlabel)
    ax.grid(axis="x", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)

    # Legend outside
    ax.legend(
        frameon=False,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
    )

    # Value labels at bar ends (always positive text)
    for yi, (ru, eu) in enumerate(zip(d[ru_col].tolist(), d[eu_col].tolist())):
        if ru > 0:
            ax.text(-ru - 0.2, yi, str(int(ru)), va="center", ha="right", fontsize=8, color=RU_COLOR)
        if eu > 0:
            ax.text(eu + 0.2, yi, str(int(eu)), va="center", ha="left", fontsize=8, color=EU_COLOR)

    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    input_path = Path("results/pairs/pairs_summary.csv")
    out_dir = Path("Plots/permissions_pairs")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise SystemExit(f"Missing input: {input_path}")

    df = pd.read_csv(input_path)

    needed = {
        "ru_perm_count_local", "eu_perm_count_local",
        "ru_vt_dangerous_perm_count", "eu_vt_dangerous_perm_count",
        "ru_app", "eu_app",
    }
    missing = needed - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}\nFound: {list(df.columns)}")

    mirrored_barplot(
        df=df,
        ru_col="ru_perm_count_local",
        eu_col="eu_perm_count_local",
        title=TITLE_1,
        explanation=EXPL_1,
        out_png=out_dir / "mirrored_perm_local.png",
        out_svg=out_dir / "mirrored_perm_local.svg",
        xlabel="Permissions count (RU left, EU right)",
    )

    mirrored_barplot(
        df=df,
        ru_col="ru_vt_dangerous_perm_count",
        eu_col="eu_vt_dangerous_perm_count",
        title=TITLE_2,
        explanation=EXPL_2,
        out_png=out_dir / "mirrored_vt_dangerous_perm.png",
        out_svg=out_dir / "mirrored_vt_dangerous_perm.svg",
        xlabel="Dangerous permissions count (RU left, EU right)",
    )

    print("Saved plots to:", out_dir)


if __name__ == "__main__":
    main()
