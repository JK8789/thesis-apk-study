#!/usr/bin/env python3
"""
Divergent barplots for paired RU vs EU comparisons.

Creates two plots:
  1) Δ local permissions = ru_perm_count_local - eu_perm_count_local
  2) Δ dangerous permissions = ru_vt_dangerous_perm_count - eu_vt_dangerous_perm_count

Input:
  results/pairs/pairs_summary.csv

Output (plots only):
  Plots/permissions_pairs/divergent_delta_perm_local.png
  Plots/permissions_pairs/divergent_delta_perm_local.svg
  Plots/permissions_pairs/divergent_delta_vt_dangerous.png
  Plots/permissions_pairs/divergent_delta_vt_dangerous.svg

Run from thesis-apk-study/:
  python3 scripts/create_plots/create_permissions_divergent_barplot.py
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


TITLE_1 = "Paired comparison (divergent): Δ total permissions (RU − EU)"
EXPL_1 = (
    "Each bar represents one matched RU–EU app pair. Values are computed as RU minus EU; "
    "positive values mean the RU app requests more permissions, negative values mean the EU app requests more."
)

TITLE_2 = "Paired comparison (divergent): Δ dangerous permissions (RU − EU)"
EXPL_2 = (
    "Each bar represents one matched RU–EU app pair. Values are computed as RU minus EU using VirusTotal "
    "dangerous permission counts; positive values mean RU > EU, negative values mean EU > RU."
)


def divergent_barplot(
    df: pd.DataFrame,
    ru_col: str,
    eu_col: str,
    title: str,
    explanation: str,
    out_png: Path,
    out_svg: Path,
    ylabel: str,
    label_col: str = "pair_id",
) -> None:
    d = df.copy()

    d[ru_col] = pd.to_numeric(d[ru_col], errors="coerce")
    d[eu_col] = pd.to_numeric(d[eu_col], errors="coerce")
    d = d.dropna(subset=[ru_col, eu_col]).reset_index(drop=True)

    # delta RU - EU
    d["delta"] = d[ru_col] - d[eu_col]

    # labels: pair_id if exists else app names
    if label_col in d.columns:
        d["label"] = d[label_col].astype(str)
    elif {"ru_app", "eu_app"}.issubset(d.columns):
        d["label"] = d["ru_app"].astype(str) + " vs " + d["eu_app"].astype(str)
    else:
        d["label"] = [f"pair_{i+1}" for i in range(len(d))]

    # sort by delta for readability
    d = d.sort_values("delta", ascending=True).reset_index(drop=True)

    # colors based on sign
    colors = ["tab:orange" if v < 0 else ("tab:blue" if v > 0 else "gray") for v in d["delta"].tolist()]

    fig = plt.figure(figsize=(12, max(6, len(d) * 0.28)), dpi=200)
    fig.subplots_adjust(top=0.86)

    fig.suptitle(title, fontsize=16, y=0.97)
    fig.text(0.5, 0.91, explanation, ha="center", va="top", fontsize=10)

    ax = fig.add_subplot(111)

    y = list(range(len(d)))
    ax.barh(y, d["delta"].tolist(), color=colors)

    ax.axvline(0, linewidth=1.2, alpha=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(d["label"].tolist())
    ax.set_xlabel(ylabel)

    ax.grid(axis="x", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)

    # add small value labels near bar ends
    for yi, val in enumerate(d["delta"].tolist()):
        if val == 0:
            continue
        ha = "left" if val > 0 else "right"
        x_text = val + (0.15 if val > 0 else -0.15)
        ax.text(x_text, yi, f"{val:.0f}", va="center", ha=ha, fontsize=8)

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
    }
    missing = needed - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}\nFound: {list(df.columns)}")

    divergent_barplot(
        df=df,
        ru_col="ru_perm_count_local",
        eu_col="eu_perm_count_local",
        title=TITLE_1,
        explanation=EXPL_1,
        out_png=out_dir / "divergent_delta_perm_local.png",
        out_svg=out_dir / "divergent_delta_perm_local.svg",
        ylabel="Δ permissions (RU − EU)",
        label_col="pair_id",
    )

    divergent_barplot(
        df=df,
        ru_col="ru_vt_dangerous_perm_count",
        eu_col="eu_vt_dangerous_perm_count",
        title=TITLE_2,
        explanation=EXPL_2,
        out_png=out_dir / "divergent_delta_vt_dangerous.png",
        out_svg=out_dir / "divergent_delta_vt_dangerous.svg",
        ylabel="Δ dangerous permissions (RU − EU)",
        label_col="pair_id",
    )

    print("Saved plots to:", out_dir)


if __name__ == "__main__":
    main()
