import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Plots" / "thesis_plot_scripts_real"
OUT.mkdir(parents=True, exist_ok=True)

PAIR_ORDER = [
    'maps', 'taxi', 'rail1', 'rail2',
    'ecom1', 'ecom2', 'ecom3', 'ecom4',
    'bank1', 'bank2', 'bank3', 'bank4',
    'health', 'social1', 'social2',
    'msg1', 'msg2', 'gov1', 'gov2', 'gov3'
]

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

pairs = pd.read_csv(ROOT / "results/local/extracted_local_manifest_features and lists.csv")
local = pd.read_csv(ROOT / "results/local/local_from_manifest.csv")

df = pairs.merge(local, on="sha256", how="inner")

df["exported_components"] = (
    df["exported_act_true"].fillna(0)
    + df["exported_srv_true"].fillna(0)
    + df["exported_rcv_true"].fillna(0)
    + df["exported_prv_true"].fillna(0)
)

df = df[["pair_id", "group", "exported_components"]].drop_duplicates()

wide = df.pivot_table(
    index="pair_id",
    columns="group",
    values="exported_components",
    aggfunc="first"
).reset_index()

wide["pair_id"] = pd.Categorical(wide["pair_id"], categories=PAIR_ORDER, ordered=True)
wide = wide.sort_values("pair_id").dropna(subset=["ru", "eu"])

wide["diff_ru_minus_eu"] = wide["ru"] - wide["eu"]
wide = wide.sort_values("diff_ru_minus_eu")

y = np.arange(len(wide))

fig, ax = plt.subplots(figsize=(11, 8))

colors = np.where(wide["diff_ru_minus_eu"] >= 0, "#7FB77E", "#C44A3A")
ax.hlines(y=y, xmin=0, xmax=wide["diff_ru_minus_eu"], color=colors, linewidth=2.5)
ax.scatter(wide["diff_ru_minus_eu"], y, color=colors, s=55, zorder=3)

ax.axvline(0, color="black", linewidth=1)
ax.set_yticks(y)
ax.set_yticklabels([PAIR_LABELS[p] for p in wide["pair_id"]], fontsize=10)
ax.set_xlabel("Difference in exported components (RU - EU)")
ax.set_title("Difference in exported Android components by matched RU-EU app pair", fontsize=16, pad=12)
ax.grid(axis="x", linestyle=":", alpha=0.35)

fig.tight_layout()
out = OUT / "fig6_4_exported_components_lollipop_diff.png"
fig.savefig(out, dpi=300, bbox_inches="tight")
print(out)
