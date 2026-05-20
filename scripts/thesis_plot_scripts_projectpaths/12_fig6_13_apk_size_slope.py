
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
pivot = df.pivot_table(index="apk_filename", columns="store", values="size_bytes", aggfunc="first") / (1024*1024)
pivot = pivot.reset_index().sort_values("apk_filename")
fig, ax = plt.subplots(figsize=(10,7))
x0, x1 = 0, 1
for _, row in pivot.iterrows():
    ax.plot([x0, x1], [row["Google Play"], row["RuStore"]], color="#90A4AE", linewidth=1.8, alpha=0.9)
    ax.scatter([x0], [row["Google Play"]], color="#FB8C00", s=50)
    ax.scatter([x1], [row["RuStore"]], color="#1E88E5", s=50)
    ax.text(x0-0.02, row["Google Play"], row["apk_filename"], ha="right", va="center", fontsize=8)
ax.set_xlim(-0.35, 1.2)
ax.set_xticks([x0, x1]); ax.set_xticklabels(["Google Play", "RuStore"])
ax.set_ylabel("APK size (MB)")
ax.set_title("APK size comparison across stores (slope chart)", fontsize=16, pad=12)
ax.grid(axis="y", linestyle=":", alpha=0.35)
fig.tight_layout()
fig.savefig(OUT / "fig6_13_apk_size_slope.png", dpi=300, bbox_inches="tight")
print(OUT / "fig6_13_apk_size_slope.png")
