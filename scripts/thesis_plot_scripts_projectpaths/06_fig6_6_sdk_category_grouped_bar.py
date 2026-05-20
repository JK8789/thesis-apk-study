
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT
OUT = ROOT / "Plots" / "thesis_plot_scripts_real"
OUT.mkdir(parents=True, exist_ok=True)

PAIR_ORDER = ['maps', 'taxi', 'rail1', 'rail2', 'ecom1', 'ecom2', 'ecom3', 'ecom4', 'bank1', 'bank2', 'bank3', 'bank4', 'health', 'social1', 'social2', 'msg1', 'msg2', 'gov1', 'gov2', 'gov3']
PAIR_LABELS = {
    'maps': 'Yandex Maps vs Google Maps',
    'taxi': 'Yandex Go Taxi vs Bolt',
    'rail1': 'RZD vs DB Navigator',
    'rail2': 'Yandex Trains vs Mobiliteit.lu',
    'ecom1': 'Ozon vs Amazon Shopping',
    'ecom2': 'Wildberries vs Zalando',
    'ecom3': 'Yandex Market vs bol',
    'ecom4': 'Avito vs Vinted',
    'bank1': 'Sberbank vs BGL',
    'bank2': 'Tinkoff vs ING Luxembourg',
    'bank3': 'Alfa Bank vs Revolut',
    'bank4': 'VTB vs BILnet',
    'health': 'EMIAS.INFO vs Doctena',
    'social1': 'VK vs Facebook',
    'social2': 'OK vs X',
    'msg1': 'MAX vs WhatsApp',
    'msg2': 'Yandex Telemost vs Telegram',
    'gov1': 'Gosuslugi vs MyGuichet.lu',
    'gov2': 'Nalogi FL vs impots.gouv',
    'gov3': 'Gosuslugi Biometria vs itsme',
}


def order_pairs(df, col="pair_id"):
    df = df.copy()
    df[col] = pd.Categorical(df[col], categories=PAIR_ORDER, ordered=True)
    return df.sort_values(col)

# grouped bar for ads / analytics / network / payments
files = {
    "ads": DATA / "data/dicts/mvnrepo/ads/hits_summary_region_ads.csv",
    "analytics": DATA / "data/dicts/mvnrepo/analytics/hits_summary_region_analytics.csv",
    "network": DATA / "data/dicts/mvnrepo/network/hits_summary_region_network.csv",
}
payments_path = DATA / "data/dicts/mvnrepo/payments/hits_summary_region_pyaments.csv"
if payments_path.exists():
    files["payments"] = payments_path

rows = []
for tag, path in files.items():
    df = pd.read_csv(path)
    # aggregate apps_with_prefix over unique prefixes
    count_col = "apps_with_prefix" if "apps_with_prefix" in df.columns else df.columns[-1]
    tmp = df.groupby("region", as_index=False)[count_col].sum()
    for _, r in tmp.iterrows():
        rows.append({"tag": tag, "region": r["region"], "value": r[count_col]})
plot = pd.DataFrame(rows)

pivot = plot.pivot(index="tag", columns="region", values="value").fillna(0).reindex(list(files.keys()))
x = np.arange(len(pivot))
w = 0.35

fig, ax = plt.subplots(figsize=(9, 6))
ax.bar(x - w/2, pivot.get("ru", pd.Series([0]*len(x), index=pivot.index)), width=w, color="#5E35B1", label="RU")
ax.bar(x + w/2, pivot.get("eu", pd.Series([0]*len(x), index=pivot.index)), width=w, color="#43A047", label="EU")
for i, tag in enumerate(pivot.index):
    if "ru" in pivot.columns:
        ax.text(i - w/2, pivot.loc[tag, "ru"] + 0.5, int(pivot.loc[tag, "ru"]), ha="center", fontsize=9)
    if "eu" in pivot.columns:
        ax.text(i + w/2, pivot.loc[tag, "eu"] + 0.5, int(pivot.loc[tag, "eu"]), ha="center", fontsize=9)

ax.set_xticks(x)
ax.set_xticklabels([t.capitalize() for t in pivot.index])
ax.set_ylabel("Sum of apps_with_prefix")
ax.set_title("Third-party Maven SDK presence by category and region", fontsize=16, pad=12)
ax.legend(frameon=False)
ax.grid(axis="y", linestyle=":", alpha=0.35)
fig.tight_layout()
fig.savefig(OUT / "fig6_6_sdk_category_grouped_bar.png", dpi=300, bbox_inches="tight")
print(OUT / "fig6_6_sdk_category_grouped_bar.png")
