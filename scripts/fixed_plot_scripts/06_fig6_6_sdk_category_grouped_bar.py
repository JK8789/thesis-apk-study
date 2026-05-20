
import pandas as pd, matplotlib.pyplot as plt, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Plots' / 'thesis_plot_scripts_projectpaths'; OUT.mkdir(parents=True, exist_ok=True)
files = {
    'Ads': ROOT/'data/dicts/mvnrepo/ads/hits_summary_region_ads.csv',
    'Analytics': ROOT/'data/dicts/mvnrepo/analytics/hits_summary_region_analytics.csv',
    'Network': ROOT/'data/dicts/mvnrepo/network/hits_summary_region_network.csv',
    'Payments': ROOT/'data/dicts/mvnrepo/payments/hits_summary_region_pyaments.csv',
}
rows=[]
for cat, fp in files.items():
    df=pd.read_csv(fp); df.columns=[c.strip() for c in df.columns]
    region_col=[c for c in df.columns if c.lower()=='region'][0]
    val_col=[c for c in df.columns if c.lower() in ['apps_with_prefix','sum_apps_with_prefix','count','hits']][0]
    reg=df.groupby(region_col, as_index=False)[val_col].sum()
    for _,r in reg.iterrows():
        rows.append({'category':cat,'region':str(r[region_col]).lower(),'value':r[val_col]})
plot=pd.DataFrame(rows)
wide=plot.pivot_table(index='category',columns='region',values='value',aggfunc='sum').reindex(['Ads','Analytics','Network','Payments']).fillna(0)
x=np.arange(len(wide)); w=0.35
ru_color,eu_color='#3852B4','#FF8C00'
fig,ax=plt.subplots(figsize=(9.2,6.2))
b1=ax.bar(x-w/2, wide.get('ru',pd.Series([0]*len(wide),index=wide.index)), width=w, color=ru_color, label='RU')
b2=ax.bar(x+w/2, wide.get('eu',pd.Series([0]*len(wide),index=wide.index)), width=w, color=eu_color, label='EU')
for bars in [b1,b2]:
    for b in bars:
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+1, f'{int(b.get_height())}', ha='center', fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(wide.index, fontsize=11)
ax.set_ylabel('Cumulative Maven SDK prefix occurrences', fontsize=11)
ax.set_title('Third-party Maven SDK presence by category and region', fontsize=14, pad=12)
ax.grid(axis='y', linestyle=':', linewidth=0.8, alpha=0.18)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.legend(frameon=False, loc='upper right')
fig.tight_layout(); out=OUT/'fig6_6_sdk_category_grouped_bar.png'; fig.savefig(out,dpi=300,bbox_inches='tight'); print(out)
