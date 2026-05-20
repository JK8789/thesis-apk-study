
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

df = pd.read_csv(DATA / "dataset2/dataset2.csv")
# keep one row per app, use RuStore - Google Play difference from RuStore row if available
wide = df.pivot_table(index="apk_filename", columns="store", values=[
    "activities_all","activities_exported","services_all","services_exported",
    "receivers_all","receivers_exported","providers_all","providers_exported"
], aggfunc="first")
# compute RuStore - Google Play
metrics = ["activities_all","activities_exported","services_all","services_exported",
    "receivers_all","receivers_exported","providers_all","providers_exported"]
diff = pd.DataFrame(index=wide.index)
for m in metrics:
    diff[m] = wide[(m, "RuStore")] - wide[(m, "Google Play")]
diff = diff.loc[sorted(diff.index)]
fig, ax = plt.subplots(figsize=(10,6))
im = ax.imshow(diff.values, aspect="auto", cmap="coolwarm")
ax.set_xticks(np.arange(len(metrics)))
ax.set_xticklabels(metrics, rotation=35, ha="right")
ax.set_yticks(np.arange(len(diff.index)))
ax.set_yticklabels(diff.index, fontsize=9)
for i in range(diff.shape[0]):
    for j in range(diff.shape[1]):
        ax.text(j, i, int(diff.iloc[i,j]), ha="center", va="center", fontsize=8, color="black")
ax.set_title("Cross-store component differences (RuStore - Google Play)", fontsize=15, pad=12)
cbar = fig.colorbar(im, ax=ax)
cbar.set_label("Difference in count")
fig.tight_layout()
fig.savefig(OUT / "fig6_16_to_23_store_components_heatmap.png", dpi=300, bbox_inches="tight")
print(OUT / "fig6_16_to_23_store_components_heatmap.png")
