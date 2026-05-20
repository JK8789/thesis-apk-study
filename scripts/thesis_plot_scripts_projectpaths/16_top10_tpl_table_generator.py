
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

# Generates two CSV tables: top-10 libraries in RU and EU
df = pd.read_csv(DATA / "results/libs_longest/libs_summary_region.csv")
count_col = "apps_with_library" if "apps_with_library" in df.columns else df.columns[-1]
prefix_col = "library_prefix" if "library_prefix" in df.columns else "prefix"
for region in ["ru","eu"]:
    out = df[df["region"].str.lower().eq(region)].sort_values(count_col, ascending=False).head(10)[[prefix_col, count_col]]
    out.to_csv(OUT / f"top10_libraries_{region}.csv", index=False)
    print(OUT / f"top10_libraries_{region}.csv")
