import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Plots" / "thesis_plot_scripts_projectpaths"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(ROOT / "results/native/native_libs_per_app.csv")

# Flag apps that contain at least one native .so library
df["has_native_so"] = df["native_so_count_total"].fillna(0) > 0

# Percentage by region
summary = (
    df.groupby("region", as_index=False)["has_native_so"]
      .mean()
)

summary["percent"] = summary["has_native_so"] * 100
summary["region"] = summary["region"].str.lower()

# Keep consistent order
summary["region"] = pd.Categorical(summary["region"], categories=["ru", "eu"], ordered=True)
summary = summary.sort_values("region")

labels = ["RU applications", "EU applications"]
colors = ["#1E88E5", "#FB8C00"]

fig, ax = plt.subplots(figsize=(7, 5))

bars = ax.bar(labels, summary["percent"], color=colors, width=0.6)

for bar, value in zip(bars, summary["percent"]):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        value + 1,
        f"{value:.1f}%",
        ha="center",
        va="bottom",
        fontsize=11
    )

ax.set_ylabel("Applications with at least one native .so library (%)")
ax.set_ylim(0, 100)
ax.set_title("Prevalence of native .so libraries in RU and EU applications", fontsize=14, pad=12)
ax.grid(axis="y", linestyle=":", alpha=0.35)

fig.tight_layout()
out = OUT / "fig6_8_native_so_prevalence_bar.png"
fig.savefig(out, dpi=300, bbox_inches="tight")
print(out)
