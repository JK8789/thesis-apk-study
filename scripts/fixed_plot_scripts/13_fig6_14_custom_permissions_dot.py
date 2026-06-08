import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Plots" / "thesis_plot_scripts_projectpaths"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(ROOT / "dataset2/dataset2.csv")
df.columns = [c.strip() for c in df.columns]

required = ["apk_filename", "store", "custom_permissions_count"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}\nAvailable columns: {df.columns.tolist()}")

# Keep only needed columns
work = df[["apk_filename", "store", "custom_permissions_count"]].copy()

# Clean app names
work["app"] = (
    work["apk_filename"]
    .astype(str)
    .str.replace(".apk", "", regex=False)
    .str.replace("_", " ", regex=False)
)

# Pivot to Play vs RuStore
wide = work.pivot_table(
    index="app",
    columns="store",
    values="custom_permissions_count",
    aggfunc="first"
).reset_index()

# Normalize expected store names
wide.columns.name = None
store_map = {}
for c in wide.columns:
    cl = str(c).strip().lower()
    if cl == "google play":
        store_map[c] = "Google Play"
    elif cl == "rustore":
        store_map[c] = "RuStore"
wide = wide.rename(columns=store_map)

if "Google Play" not in wide.columns or "RuStore" not in wide.columns:
    raise ValueError(f"Expected 'Google Play' and 'RuStore' columns after pivot. Got: {wide.columns.tolist()}")

wide["same"] = wide["Google Play"] == wide["RuStore"]
wide["abs_diff"] = (wide["Google Play"] - wide["RuStore"]).abs()

# Order: changed apps first, then by difference size, then unchanged
wide = wide.sort_values(["same", "abs_diff", "app"], ascending=[True, False, True]).reset_index(drop=True)

x = np.arange(len(wide))
bar_w = 0.34

gp_color = "#F08D39"   # Google Play
rs_color = "#3852B4"   # RuStore

fig, ax = plt.subplots(figsize=(11, 6))

for i, row in wide.iterrows():
    gp_val = row["Google Play"]
    rs_val = row["RuStore"]

    if row["same"]:
        # unchanged: white fill, colored edges
        ax.bar(i - bar_w/2, gp_val, width=bar_w, color="white", edgecolor=gp_color, linewidth=1.6)
        ax.bar(i + bar_w/2, rs_val, width=bar_w, color="white", edgecolor=rs_color, linewidth=1.6)
    else:
        # changed: solid colored
        ax.bar(i - bar_w/2, gp_val, width=bar_w, color=gp_color, edgecolor="black", linewidth=0.7)
        ax.bar(i + bar_w/2, rs_val, width=bar_w, color=rs_color, edgecolor="black", linewidth=0.7)

ax.set_xticks(x)
ax.tick_params(axis='x', labelsize=15)
ax.set_xticklabels(wide["app"], rotation=25, ha="center")
ax.set_ylabel("Custom permissions count", fontsize=15)
ax.set_xlabel("Applications", fontsize=15)
ax.set_title("Custom permissions by store", fontsize=15, pad=12)
ax.grid(axis="y", linestyle=":", alpha=0.25)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.tick_params(axis='y', labelsize=15)
# Legend just below title
legend_handles = [
    Patch(facecolor=gp_color, edgecolor="black", label="Google Play"),
    Patch(facecolor=rs_color, edgecolor="black", label="RuStore"),
]
ax.legend(
    handles=legend_handles,
    loc="upper center",
    bbox_to_anchor=(0.5, 1.00),
    ncol=2,
    frameon=False,
    columnspacing=1.5,
    handletextpad=0.6,
    fontsize=15
)

fig.tight_layout()
out = OUT / "fig6_20_custom_permissions_dot.png"
fig.savefig(out, dpi=300, bbox_inches="tight")
print(out)
