import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Plots" / "thesis_plot_scripts_projectpaths"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(ROOT / "results/datasafety/datasafety_pairs_purpose.csv")
df.columns = [c.strip() for c in df.columns]

df["none_declared"] = (
    df["collected_count"].fillna(0).astype(int).eq(0) &
    df["shared_count"].fillna(0).astype(int).eq(0)
)

summary = (
    df.groupby("region", as_index=False)
      .agg(
          none_declared=("none_declared", "sum"),
          total_apps=("app_name", "count")
      )
)

summary["region"] = summary["region"].astype(str).str.strip().str.lower()
summary["region"] = pd.Categorical(summary["region"], categories=["ru", "eu"], ordered=True)
summary = summary.sort_values("region")

full = pd.DataFrame({"region": pd.Categorical(["ru", "eu"], categories=["ru", "eu"], ordered=True)})
summary = full.merge(summary, on="region", how="left")
summary["none_declared"] = summary["none_declared"].fillna(0).astype(int)
summary["total_apps"] = summary["total_apps"].fillna(20).astype(int)
summary["percent"] = (summary["none_declared"] / summary["total_apps"]) * 100

labels = ["RU applications", "EU applications"]
values = summary["percent"].tolist()
counts = summary["none_declared"].tolist()
totals = summary["total_apps"].tolist()
colors = ["#4C78A8", "#F58518"]

fig, ax = plt.subplots(figsize=(7.2, 4.8))
bars = ax.bar(labels, values, color=colors, width=0.58)

for bar, count, total, pct in zip(bars, counts, totals, values):
    y = pct + 0.8 if pct > 0 else 0.8
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        y,
        f"{count}/{total} ({pct:.0f}%)",
        ha="center",
        va="bottom",
        fontsize=10
    )

ax.set_ylabel("Applications with no declared collected or shared data (%)", fontsize=11)
ax.set_ylim(0, 30)
ax.set_title("Applications declaring no collected and no shared data", fontsize=14, pad=10)
ax.grid(axis="y", linestyle=":", alpha=0.35)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

fig.tight_layout()
out = OUT / "fig6_10_data_safety_none_bar.png"
fig.savefig(out, dpi=300, bbox_inches="tight")
print(out)
